import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from helium.common import enums
from helium.common.services import pushservice
from helium.common.tasks import send_dismiss_pushes, send_pushes
from helium.common.utils import datetimeutils, metricutils, taskutils
from helium.planner.models import Event, Homework, Reminder
from helium.planner.serializers.pushserializer import PushReminderSerializer

logger = logging.getLogger(__name__)


def _push_body(reminder):
    all_day = False
    if reminder.calendar_item:
        local_time = timezone.localtime(reminder.occurrence_bounds()[0])
        all_day = reminder.calendar_item.all_day
    elif reminder.course:
        class_start = reminder.start_of_range + datetimeutils.offset_to_timedelta(reminder.offset, reminder.offset_type)
        local_time = timezone.localtime(class_start)
    else:
        return reminder.message

    if all_day:
        return f'{reminder.message} · {local_time:%a}'

    return f'{reminder.message} · {datetimeutils.format_short_time(local_time, reminder.get_user().settings)}'


def _offset_label(reminder):
    unit = enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]
    if reminder.offset == 1:
        unit = unit.rstrip('s')
    return f'{reminder.offset} {unit}'


def _item_series_key(reminder):
    return (reminder.homework_id, reminder.event_id, reminder.user_id, reminder.type, reminder.offset,
            reminder.offset_type)


def _create_next_item_reminder(reminder):
    parent_field, model, pk = (('homework', Homework, reminder.homework_id) if reminder.homework_id
                               else ('event', Event, reminder.event_id))
    with transaction.atomic():
        item = model.objects.select_for_update().filter(pk=pk).first()
        if item is None or not item.recurrence_rule:
            return None

        series = series_filter(reminder)
        if Reminder.objects.active().filter(**series).exclude(pk=reminder.pk).exists():
            return None

        new_reminder = Reminder(
            message=reminder.message,
            offset=reminder.offset,
            offset_type=reminder.offset_type,
            type=reminder.type,
            sent=False,
            dismissed=False,
            user=reminder.user,
            **{parent_field: item},
        )

        fired_start, _ = reminder.occurrence_bounds()
        next_start = new_reminder.next_occurrence_start(after_datetime=fired_start)
        if next_start is None:
            return None

        new_reminder.save()
        return new_reminder


def get_subject(reminder):
    offset = _offset_label(reminder)
    if reminder.homework:
        calendar_item = reminder.homework
        subject = f'{calendar_item.title} in {calendar_item.course.title} in {offset}'
    elif reminder.event:
        subject = f'{reminder.event.title} in {offset}'
    elif reminder.course:
        subject = f'{reminder.course.title} in {offset}'
    else:
        return None

    return subject


_SERIES_FIELDS = ('course', 'user', 'type', 'offset', 'offset_type')


def heal_orphaned_repeating_reminders(user_id=None):
    """
    Periodic maintenance for repeating reminder series: courses, then repeating Homework and Events.

    Series with no active reminder whose course has ended in every timezone are skipped.

    Phase 1 — collect series state and build delete list: for each series, examine the unsent
    undismissed reminder (at most one per series). If it is stale (start_of_range past the send
    window), mark it for deletion. Sent reminders are intentionally past their window and are
    never touched here. Templates for series that will have no active unsent reminder after
    cleanup are collected before any deletions occur.

    Phase 2 — delete stale unsent reminders.

    Phase 3 — recreate missing successors: any series that ends up with no active
    (unsent + undismissed) reminder gets a new occurrence created using the template
    collected in phase 1.

    :param user_id: Optional user ID to scope the operation to a single user. When None (default),
        operates globally across all users.
    """
    now = timezone.now()
    window_start = now - timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES)

    series = Reminder.objects.repeating().filter(
        Q(sent=False, dismissed=False) | Q(course__end_date__gte=datetimeutils.earliest_local_date()))
    if user_id is not None:
        series = series.for_user(user_id)

    all_series = list(
        series
        .values(*_SERIES_FIELDS)
        .distinct()
    )

    active_by_series = {
        tuple(row[field] for field in _SERIES_FIELDS): row
        for row in series.active().values('pk', 'start_of_range', *_SERIES_FIELDS)
    }

    to_delete_pks = []
    orphaned_keys = set()

    for combo in all_series:
        series_key = tuple(combo[field] for field in _SERIES_FIELDS)
        unsent = active_by_series.get(series_key)

        stale = unsent and (unsent['start_of_range'] is None or unsent['start_of_range'] <= window_start)

        if stale:
            to_delete_pks.append(unsent['pk'])

        if stale or not unsent:
            orphaned_keys.add(series_key)

    latest_pk_in_series = (
        Reminder.objects
        .filter(**{field: OuterRef(field) for field in _SERIES_FIELDS})
        .order_by('-start_of_range')
        .values('pk')[:1]
    )
    successor_templates = [
        reminder for reminder in (
            Reminder.objects
            .filter(course_id__in={key[0] for key in orphaned_keys}, pk=Subquery(latest_pk_in_series))
            .select_related('user', 'user__settings', 'course', 'course__course_group')
            .prefetch_related('course__schedules')
        )
        if (reminder.course_id, reminder.user_id, reminder.type, reminder.offset,
            reminder.offset_type) in orphaned_keys
    ]

    if to_delete_pks:
        logger.info(f'Deleting {len(to_delete_pks)} stale reminder(s)')
        Reminder.objects.filter(pk__in=to_delete_pks).delete()

    for reminder in successor_templates:
        series = series_filter(reminder)
        if Reminder.objects.active().filter(**series).exists():
            continue
        try:
            logger.info(
                f'Healing orphaned repeating reminder series for course {reminder.course_id}, user {reminder.user_id}')
            create_next_repeating_reminder(reminder)
        except Exception:
            logger.error("An error occurred healing orphaned repeating reminder.", exc_info=True)

    heal_repeating_item_reminders(user_id=user_id)


def clone_reminders(source, target):
    """
    Copy reminders from source onto target, once per series when source repeats. Both must be Homework or Event;
    ``start_of_range`` re-anchors via ``Reminder.save()``.
    """
    if not isinstance(source, (Homework, Event)):
        raise ValueError(
            f'clone_reminders source must be a Homework or Event, got {type(source).__name__}')
    if not isinstance(target, (Homework, Event)):
        raise ValueError(
            f'clone_reminders target must be a Homework or Event, got {type(target).__name__}')

    parent_field = 'homework' if isinstance(target, Homework) else 'event'
    user = target.get_user()

    reminders = list(source.reminders.all())
    if source.recurrence_rule:
        by_series = {}
        for reminder in sorted(reminders, key=lambda r: (not r.sent, r.start_of_range or timezone.now())):
            by_series[(reminder.type, reminder.offset, reminder.offset_type)] = reminder
        reminders = list(by_series.values())

    for reminder in reminders:
        Reminder.objects.create(
            message=reminder.message,
            offset=reminder.offset,
            offset_type=reminder.offset_type,
            type=reminder.type,
            user=user,
            **{parent_field: target},
        )


def delete_reminder_series(reminder):
    """Delete every reminder in a repeating item reminder's series, fired records included."""
    Reminder.objects.filter(**series_filter(reminder)).delete()


def delete_fired_reminders(series):
    """Delete the fired records of the reminder series matching ``series`` (a :func:`series_filter`)."""
    Reminder.objects.filter(sent=True, **series).delete()


def collapse_reminder_series(item):
    """
    Drop the fired records of an item's reminder series that still have an active reminder, for when the item stops
    repeating and each series becomes a single reminder again.
    """
    reminders = list(item.reminders.all())
    active_keys = {(r.user_id, r.type, r.offset, r.offset_type) for r in reminders if not r.sent and not r.dismissed}
    fired_pks = [r.pk for r in reminders if r.sent and (r.user_id, r.type, r.offset, r.offset_type) in active_keys]
    if fired_pks:
        Reminder.objects.filter(pk__in=fired_pks).delete()


def series_filter(reminder):
    """The lookup that matches every reminder in ``reminder``'s repeating series."""
    if reminder.course_id:
        parent = dict(course=reminder.course)
    elif reminder.homework_id:
        parent = dict(homework=reminder.homework)
    else:
        parent = dict(event=reminder.event)
    return dict(user=reminder.user, type=reminder.type, offset=reminder.offset, offset_type=reminder.offset_type,
                **parent)


def heal_repeating_item_reminders(user_id=None, homework_id=None, event_id=None):
    """
    Re-arm every repeating Homework or Event reminder series that has no active reminder, from its latest fired
    reminder. Without ``homework_id`` or ``event_id``, only series that fired within the last
    ``settings.REMINDER_REPEATING_HEAL_LOOKBACK`` are considered.
    """
    reminders = Reminder.objects.filter(Q(homework__recurrence_rule__isnull=False) |
                                        Q(event__recurrence_rule__isnull=False))
    if user_id is not None:
        reminders = reminders.for_user(user_id)
    if homework_id is not None:
        reminders = reminders.filter(homework_id=homework_id)
    if event_id is not None:
        reminders = reminders.filter(event_id=event_id)

    active_keys = {_item_series_key(reminder) for reminder in reminders.active()}

    fired = reminders.filter(sent=True).select_related('homework', 'event', 'user', 'user__settings')
    if homework_id is None and event_id is None:
        fired = fired.filter(start_of_range__gte=timezone.now() - settings.REMINDER_REPEATING_HEAL_LOOKBACK)

    latest_fired = {_item_series_key(reminder): reminder for reminder in fired.order_by('start_of_range')}

    for key, template in latest_fired.items():
        if key in active_keys:
            continue
        try:
            create_next_repeating_reminder(template)
        except Exception:
            logger.error("An error occurred healing a repeating item reminder.", exc_info=True)


def create_next_repeating_reminder(reminder):
    """
    For a repeating reminder (course, or a Homework or Event with a recurrence rule), create the next occurrence.

    Passes the fired occurrence's start time as after_datetime so the search begins strictly after
    the occurrence that just fired, preventing the same occurrence from being queued again. Guards
    against duplicate creation (e.g. concurrent workers) by checking for an existing active
    (unsent + undismissed) reminder for the same series before saving.
    """
    if reminder.homework_id or reminder.event_id:
        return _create_next_item_reminder(reminder)

    if not reminder.course_id:
        return None

    series = series_filter(reminder)

    if Reminder.objects.active().filter(**series).exclude(pk=reminder.pk).exists():
        return None

    # Compute the start time of the class that just fired so we skip it when searching.
    offset_delta = datetimeutils.offset_to_timedelta(reminder.offset, reminder.offset_type)
    fired_class_start = reminder.start_of_range + offset_delta if reminder.start_of_range else None

    new_reminder = Reminder(
        message=reminder.message,
        offset=reminder.offset,
        offset_type=reminder.offset_type,
        type=reminder.type,
        sent=False,
        dismissed=False,
        course=reminder.course,
        user=reminder.user
    )

    next_start = new_reminder._get_next_course_occurrence_start(after_datetime=fired_class_start)
    if next_start:
        new_reminder.start_of_range = next_start - offset_delta
        new_reminder.save()
        return new_reminder

    return None


def clear_delivered_push(reminder):
    """
    Clear a delivered reminder's notification from the user's devices.

    A reschedule that un-sends a reminder leaves the old notification in the tray with nothing to
    clear it: it is no longer `sent`, so it drops out of the notification list and cannot be
    dismissed.
    """
    push_tokens = pushservice.get_push_tokens(reminder.get_user())
    if not push_tokens:
        return

    taskutils.safe_apply_async(send_dismiss_pushes,
                               args=(push_tokens, reminder.pk),
                               priority=settings.CELERY_PRIORITY_HIGH)


def _delete_excess_past_reminders(just_fired):
    """
    After a repeating reminder fires, delete every other sent reminder of its series, dismissed ones included.
    Only the reminder that just fired is kept as the single past record visible in notifications. A course
    series intentionally ignores offset/offset_type so stale reminders from a previous offset (e.g. after a
    reminder edit) are also cleaned up; a Homework or Event series is keyed by offset too, as each offset is a separate
    reminder the user set.
    """
    series = series_filter(just_fired)
    if just_fired.course_id:
        series.pop('offset')
        series.pop('offset_type')

    Reminder.objects.filter(sent=True, **series).exclude(pk=just_fired.pk).delete()


def _reminder_for_processing(reminder_id, *prefetch):
    return (Reminder.objects
            .select_related('user', 'user__settings', 'homework', 'homework__course', 'event',
                            'course', 'course__course_group')
            .prefetch_related('course__schedules', *prefetch)
            .filter(pk=reminder_id)
            .first())


def _claim(reminder):
    """
    Take ownership of a reminder before anything is sent for it.

    The update only matches while the row is still unsent, so of any number of workers holding
    this reminder exactly one proceeds and the rest stop here.
    """
    if not Reminder.objects.filter(pk=reminder.pk, sent=False).update(sent=True):
        logger.info(f'Reminder {reminder.pk} was already claimed elsewhere. Nothing to do.')
        return False

    reminder.sent = True
    return True


def _continue_series(reminder, channel):
    if reminder.repeating:
        _delete_excess_past_reminders(reminder)
        try:
            new_reminder = create_next_repeating_reminder(reminder)
            if new_reminder is None:
                logger.info(
                    f'No next occurrence for repeating {channel} reminder series (series ended): '
                    f'course={reminder.course_id}, homework={reminder.homework_id}, event={reminder.event_id}, '
                    f'user={reminder.user_id}')
        except Exception:
            logger.error(f"An error occurred creating next repeating {channel} reminder.", exc_info=True)


def _email_send_args(reminder, user):
    """Everything fallible about an email send, resolved before the reminder is claimed."""
    if not (user.email and user.is_active):
        logger.warning(
            f'Reminder {reminder.pk} was not processed, as the account appears to be inactive for user {user.pk}')
        return None

    subject = get_subject(reminder)
    if not subject:
        logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned.')
        return None

    if reminder.event:
        calendar_item_id, calendar_item_type = reminder.event.pk, enums.EVENT
    elif reminder.homework:
        calendar_item_id, calendar_item_type = reminder.homework.pk, enums.HOMEWORK
    elif reminder.course:
        calendar_item_id, calendar_item_type = reminder.course.pk, enums.COURSE
    else:
        logger.warning(f'Reminder {reminder.pk} was not for a homework, event, or course. Nothing to do.')
        return None

    return user.email, subject, reminder.pk, calendar_item_id, calendar_item_type


def _push_send_args(reminder, user):
    """Everything fallible about a push send, resolved before the reminder is claimed."""
    subject = get_subject(reminder)
    if not subject:
        logger.info(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
        return None

    push_tokens = pushservice.get_push_tokens(user)
    if not push_tokens:
        metricutils.increment('action.reminder.undeliverable', user=reminder.user,
                              extra_tags=['channel:push'])
        logger.info(
            f'Reminder {reminder.pk} was not pushed, as there are no active push tokens for user {user.pk}')
        return None

    return (push_tokens, user.username, subject, _push_body(reminder),
            PushReminderSerializer(reminder).data)


def process_email_reminder(reminder_id):
    from helium.planner.tasks import send_email_reminder

    reminder = _reminder_for_processing(reminder_id)
    if reminder is None or reminder.sent:
        return

    user = reminder.get_user()

    timezone.activate(ZoneInfo(user.settings.time_zone))

    try:
        send_args = _email_send_args(reminder, user)

        if not _claim(reminder):
            return

        if send_args is not None:
            logger.info(f'Sending email reminder {reminder.pk} for user {user.pk}')

            metricutils.increment('task', user=user, extra_tags=['name:reminder.queue.email'])

            # Never critical: the synchronous fallback risks re-sending a message the broker
            # already accepted.
            taskutils.safe_apply_async(send_email_reminder,
                args=send_args,
                priority=settings.CELERY_PRIORITY_HIGH,
            )

        _continue_series(reminder, 'email')
    except Exception:
        logger.error("An error occurred processing email reminder.", exc_info=True)
    finally:
        timezone.deactivate()


def process_push_reminder(reminder_id, mark_sent_only=False):
    reminder = _reminder_for_processing(reminder_id, 'user__push_tokens')
    if reminder is None or reminder.sent:
        return

    user = reminder.get_user()

    timezone.activate(ZoneInfo(user.settings.time_zone))

    try:
        send_args = None if mark_sent_only else _push_send_args(reminder, user)

        if not _claim(reminder):
            return

        if mark_sent_only:
            logger.info(f"Marking reminder {reminder.pk} as sent without performing other actions")
        elif send_args is not None:
            logger.info(f'Sending pushes for reminder {reminder.pk} for user {user.pk}')

            metricutils.increment('task', value=len(send_args[0]), user=reminder.user,
                                  extra_tags=['name:reminder.queue.push'])

            # Never critical, for the same reason as the email send above
            taskutils.safe_apply_async(send_pushes,
                args=send_args,
                priority=settings.CELERY_PRIORITY_HIGH,
            )

        _continue_series(reminder, 'push')
    except Exception:
        logger.error("An error occurred processing push reminder.", exc_info=True)
    finally:
        timezone.deactivate()


def process_push_reminders(mark_sent_only=False):
    """Process every due push reminder inline, for callers that need it finished before returning."""
    for reminder_id in (Reminder.objects
                        .with_type(enums.PUSH)
                        .unsent()
                        .for_today()
                        .values_list('pk', flat=True)):
        process_push_reminder(reminder_id, mark_sent_only=mark_sent_only)
