import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone

from helium.common import enums
from helium.common.tasks import send_pushes
from helium.common.utils.commonutils import format_short_time
from helium.common.utils import metricutils, taskutils
from helium.planner.models import Reminder
from helium.planner.serializers.pushserializer import PushReminderSerializer

logger = logging.getLogger(__name__)


def _push_body(reminder):
    if reminder.homework:
        local_time = timezone.localtime(reminder.homework.start)
    elif reminder.event:
        local_time = timezone.localtime(reminder.event.start)
    elif reminder.course:
        class_start = reminder.start_of_range + timedelta(
            **{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
        local_time = timezone.localtime(class_start)
    else:
        return reminder.message

    return f'{reminder.message} · {format_short_time(local_time)}'


def _offset_label(reminder):
    unit = enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]
    if reminder.offset == 1:
        unit = unit.rstrip('s')
    return f'{reminder.offset} {unit}'


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


def heal_orphaned_repeating_reminders(user_id=None):
    """
    Periodic maintenance for repeating course reminder series.

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

    series = Reminder.objects.repeating()
    if user_id is not None:
        series = series.for_user(user_id)

    all_series = list(
        series
        .values('course', 'user', 'type', 'offset', 'offset_type')
        .distinct()
    )

    to_delete_pks = []
    successor_templates = []

    for combo in all_series:
        unsent = (
            Reminder.objects
            .active()
            .filter(**combo)
            .first()
        )

        stale = unsent and (unsent.start_of_range is None or unsent.start_of_range <= window_start)

        if stale:
            to_delete_pks.append(unsent.pk)

        if stale or not unsent:
            template = (
                Reminder.objects
                .filter(**combo)
                .select_related('user', 'user__settings', 'course', 'course__course_group')
                .prefetch_related('course__schedules')
                .order_by('-start_of_range')
                .first()
            )
            if template:
                successor_templates.append(template)

    if to_delete_pks:
        logger.info(f'Deleting {len(to_delete_pks)} stale reminder(s)')
        Reminder.objects.filter(pk__in=to_delete_pks).delete()

    for reminder in successor_templates:
        series_filter = dict(course=reminder.course, user=reminder.user, type=reminder.type,
                             offset=reminder.offset, offset_type=reminder.offset_type)
        if Reminder.objects.active().filter(**series_filter).exists():
            continue
        try:
            logger.info(
                f'Healing orphaned repeating reminder series for course {reminder.course_id}, user {reminder.user_id}')
            create_next_repeating_reminder(reminder)
        except Exception:
            logger.error("An error occurred healing orphaned repeating reminder.", exc_info=True)


def clone_reminders(source, target):
    """Copy reminders from source onto target. Both must be Homework or Event; ``start_of_range`` re-anchors via ``Reminder.save()``."""
    from helium.planner.models import Event, Homework

    if not isinstance(source, (Homework, Event)):
        raise ValueError(
            f'clone_reminders source must be a Homework or Event, got {type(source).__name__}')
    if not isinstance(target, (Homework, Event)):
        raise ValueError(
            f'clone_reminders target must be a Homework or Event, got {type(target).__name__}')

    parent_field = 'homework' if isinstance(target, Homework) else 'event'
    user = target.get_user()

    for reminder in source.reminders.all():
        Reminder.objects.create(
            message=reminder.message,
            offset=reminder.offset,
            offset_type=reminder.offset_type,
            type=reminder.type,
            user=user,
            **{parent_field: target},
        )


def create_next_repeating_reminder(reminder):
    """
    For a repeating reminder (course), create the next occurrence.

    Passes the fired class's start time as after_datetime so the search begins strictly after
    the class that just fired, preventing the same occurrence from being queued again. Guards
    against duplicate creation (e.g. concurrent workers) by checking for an existing active
    (unsent + undismissed) reminder for the same series before saving.
    """
    if not reminder.course_id:
        return None

    series_filter = dict(
        course=reminder.course,
        user=reminder.user,
        type=reminder.type,
        offset=reminder.offset,
        offset_type=reminder.offset_type,
    )

    if Reminder.objects.active().filter(**series_filter).exclude(pk=reminder.pk).exists():
        return None

    # Compute the start time of the class that just fired so we skip it when searching.
    offset_delta = timedelta(**{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
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


def _delete_excess_past_reminders(just_fired):
    """
    After a repeating course reminder fires, delete any other sent+undismissed reminders for
    the same course/user/type. Only the reminder that just fired is kept as the single past
    record visible in notifications. Intentionally does not filter by offset/offset_type so
    that stale reminders from a previous offset (e.g. after a reminder edit) are also cleaned up.
    """
    Reminder.objects.filter(
        course=just_fired.course,
        user=just_fired.user,
        type=just_fired.type,
        sent=True,
        dismissed=False,
    ).exclude(pk=just_fired.pk).delete()


def _reminder_for_processing(reminder_id, *prefetch):
    return (Reminder.objects
            .select_related('user', 'user__settings', 'homework', 'homework__course', 'event',
                            'course', 'course__course_group')
            .prefetch_related('course__schedules', *prefetch)
            .filter(pk=reminder_id)
            .first())


def _claim(reminder):
    """Take ownership of a reminder before anything is sent for it.

    The update only matches while the row is still unsent, so of any number of workers holding
    this reminder exactly one proceeds and the rest stop here.
    """
    if not Reminder.objects.filter(pk=reminder.pk, sent=False).update(sent=True):
        logger.info(f'Reminder {reminder.pk} was already claimed elsewhere. Nothing to do.')
        return False

    reminder.sent = True
    return True


def _continue_series(reminder, channel):
    if reminder.course_id:
        _delete_excess_past_reminders(reminder)
        try:
            new_reminder = create_next_repeating_reminder(reminder)
            if new_reminder is None:
                logger.info(
                    f'No next occurrence for repeating {channel} reminder series (course ended): '
                    f'course={reminder.course_id}, user={reminder.user_id}')
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

    push_tokens = list({t.device_id: t.token for t in user.push_tokens.all()}.values())
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

            # critical, because the reminder is already claimed: dropping the dispatch here would
            # lose the send outright rather than leave it for the next sweep
            taskutils.safe_apply_async(send_email_reminder,
                args=send_args,
                priority=settings.CELERY_PRIORITY_HIGH,
                critical=True,
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

            # critical, for the same reason as the email send above
            taskutils.safe_apply_async(send_pushes,
                args=send_args,
                priority=settings.CELERY_PRIORITY_HIGH,
                critical=True,
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
