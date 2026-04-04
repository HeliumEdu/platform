__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

import pytz
from django.conf import settings
from django.utils import timezone

from helium.auth.models.userpushtoken import UserPushToken
from helium.common import enums
from helium.common.tasks import send_text, send_pushes
from helium.common.utils.commonutils import format_short_time
from helium.common.utils import metricutils
from helium.planner.models import Reminder
from helium.planner.serializers.reminderserializer import ReminderExtendedSerializer

logger = logging.getLogger(__name__)


def _push_body(reminder):
    from datetime import timedelta
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


def heal_orphaned_repeating_reminders():
    """
    Periodic maintenance for repeating course reminder series.

    Step 1 — dismiss stale/duplicate undismissed reminders: for each series, keep only the most
    recent undismissed reminder and dismiss the rest. If that most recent reminder is itself past
    the send window (the class already started), dismiss it too so the series is clean.

    Step 2 — recreate missing successors: any series with no active (unsent + undismissed) reminder
    gets a new occurrence created. This covers both the classic orphan case (sent=True, no successor
    due to worker downtime) and series cleaned up in step 1 where all reminders were stale.
    """
    import datetime as dt
    from django.db.models import Exists, OuterRef

    now = timezone.now()
    window_start = now - dt.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES)

    # Step 1: Dismiss stale and duplicate undismissed reminders.
    active_series = (
        Reminder.objects
        .filter(repeating=True, course__isnull=False, dismissed=False)
        .values('course', 'user', 'type')
        .distinct()
    )

    for combo in active_series:
        undismissed = list(
            Reminder.objects
            .filter(dismissed=False, repeating=True, **combo)
            .order_by('-start_of_range')
        )

        if not undismissed:
            continue

        most_recent = undismissed[0]
        to_dismiss = [r.pk for r in undismissed[2:]]

        if most_recent.start_of_range <= window_start:
            if len(undismissed) > 1:
                to_dismiss.append(undismissed[1].pk)
            to_dismiss.append(most_recent.pk)

        if to_dismiss:
            logger.info(
                f'Deleting {len(to_dismiss)} stale/duplicate reminder(s) for course {combo["course"]}, user {combo["user"]}')
            Reminder.objects.filter(pk__in=to_dismiss).delete()

    # Step 2: Recreate missing successors for any series with no active unsent reminder.
    active_unsent = Reminder.objects.filter(
        sent=False,
        dismissed=False,
        repeating=True,
        course=OuterRef('course'),
        user=OuterRef('user'),
        type=OuterRef('type'),
    )

    orphaned_combos = {
        (row['course'], row['user'], row['type'])
        for row in (
            Reminder.objects
            .filter(repeating=True, course__isnull=False)
            .annotate(has_active=Exists(active_unsent))
            .filter(has_active=False)
            .values('course', 'user', 'type')
        )
    }

    for combo in [{'course': c, 'user': u, 'type': t} for c, u, t in orphaned_combos]:
        reminder = (
            Reminder.objects
            .filter(repeating=True, **combo)
            .select_related('user', 'user__settings', 'course', 'course__course_group')
            .prefetch_related('course__schedules')
            .order_by('-start_of_range')
            .first()
        )
        if reminder:
            try:
                logger.info(
                    f'Healing orphaned repeating reminder series for course {reminder.course_id}, user {reminder.user_id}')
                create_next_repeating_reminder(reminder)
            except Exception:
                logger.error("An error occurred healing orphaned repeating reminder.", exc_info=True)


def create_next_repeating_reminder(reminder):
    """
    For a repeating reminder (course), create the next occurrence.

    Passes the fired class's start time as after_datetime so the search begins strictly after
    the class that just fired, preventing the same occurrence from being queued again. Guards
    against duplicate creation (e.g. concurrent workers) by checking for an existing active
    (unsent + undismissed) reminder for the same series before saving.
    """
    if not reminder.repeating or not reminder.course:
        return None

    series_filter = dict(
        repeating=True,
        course=reminder.course,
        user=reminder.user,
        type=reminder.type,
    )

    if Reminder.objects.filter(sent=False, dismissed=False, **series_filter).exclude(pk=reminder.pk).exists():
        return None

    # Compute the start time of the class that just fired so we skip it when searching.
    from datetime import timedelta
    offset_delta = timedelta(**{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
    fired_class_start = reminder.start_of_range + offset_delta if reminder.start_of_range else None

    new_reminder = Reminder(
        title=reminder.title,
        message=reminder.message,
        offset=reminder.offset,
        offset_type=reminder.offset_type,
        type=reminder.type,
        sent=False,
        dismissed=False,
        repeating=True,
        course=reminder.course,
        user=reminder.user
    )

    next_start = new_reminder._get_next_course_occurrence_start(after_datetime=fired_class_start)
    if next_start:
        new_reminder.save()
        return new_reminder

    return None


def _delete_excess_past_reminders(just_fired):
    """
    After a repeating course reminder fires, delete any other sent+undismissed reminders for
    the same series. Only the reminder that just fired is kept as the single past record.
    """
    Reminder.objects.filter(
        repeating=True,
        course=just_fired.course,
        user=just_fired.user,
        type=just_fired.type,
        sent=True,
        dismissed=False,
    ).exclude(pk=just_fired.pk).delete()


def process_email_reminders():
    from helium.planner.tasks import send_email_reminder

    rate_per_sec = settings.EMAIL_SEND_RATE_PER_SEC
    queued_count = 0

    for reminder in (Reminder.objects
                     .with_type(enums.EMAIL)
                     .unsent()
                     .for_today()
                     .select_related('user', 'user__settings', 'homework', 'homework__course', 'event',
                                     'course', 'course__course_group')
                     .iterator()):
        user = reminder.get_user()

        timezone.activate(pytz.timezone(user.settings.time_zone))

        try:
            if user.email and user.is_active:
                subject = get_subject(reminder)

                if not subject:
                    logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned.')
                else:
                    if reminder.event:
                        calendar_item_id = reminder.event.pk
                        calendar_item_type = enums.EVENT
                    elif reminder.homework:
                        calendar_item_id = reminder.homework.pk
                        calendar_item_type = enums.HOMEWORK
                    elif reminder.course:
                        calendar_item_id = reminder.course.pk
                        calendar_item_type = enums.COURSE
                    else:
                        logger.warning(f'Reminder {reminder.pk} was not for a homework, event, or course. Nothing to do.')
                        continue

                    logger.info(f'Sending email reminder {reminder.pk} for user {user.pk}')

                    metricutils.increment('task', user=user, extra_tags=['name:reminder.queue.email'])

                    send_email_reminder.apply_async(
                        args=(user.email, subject, reminder.pk, calendar_item_id, calendar_item_type),
                        countdown=queued_count / rate_per_sec,
                        priority=settings.CELERY_PRIORITY_HIGH,
                    )
                    queued_count += 1
            else:
                logger.warning(
                    f'Reminder {reminder.pk} was not processed, as the account appears to be inactive for user {user.pk}')

            reminder.sent = True
            reminder.save()

            if reminder.repeating and reminder.course:
                _delete_excess_past_reminders(reminder)
                create_next_repeating_reminder(reminder)
        except Exception:
            logger.error("An error occurred processing email reminder.", exc_info=True)

        timezone.deactivate()


def process_text_reminders():
    for reminder in (Reminder.objects
                     .with_type(enums.TEXT)
                     .unsent()
                     .for_today()
                     .filter(course__isnull=True)
                     .select_related('user', 'user__settings', 'user__profile', 'homework', 'homework__course', 'event')
                     .iterator()):
        user = reminder.get_user()

        timezone.activate(pytz.timezone(user.settings.time_zone))

        try:
            if user.profile.phone and user.profile.phone_verified:
                subject = get_subject(reminder)
                message = f'({subject}) {_push_body(reminder)}'

                if not subject:
                    logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
                else:
                    logger.info(f'Sending text reminder {reminder.pk} for user {user.pk}')

                    metricutils.increment('task', user=user, extra_tags=['name:reminder.queue.text'])

                    send_text.apply_async(
                        args=(user.profile.phone, message),
                        priority=settings.CELERY_PRIORITY_HIGH,
                    )
            else:
                logger.warning(
                    f'Reminder {reminder.pk} was not processed, as the phone and carrier are no longer set for user {user.pk}')

            reminder.sent = True
            reminder.save()
        except Exception:
            logger.error("An error occurred processing text reminder.", exc_info=True)

        timezone.deactivate()


def process_push_reminders(mark_sent_only=False):
    for reminder in (Reminder.objects
                     .with_type(enums.PUSH)
                     .unsent()
                     .for_today()
                     .select_related('user', 'user__settings', 'homework', 'homework__course', 'event',
                                     'course', 'course__course_group')
                     .iterator()):
        user = reminder.get_user()

        timezone.activate(pytz.timezone(user.settings.time_zone))

        try:
            if not mark_sent_only:
                subject = get_subject(reminder)

                if not subject:
                    logger.info(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
                else:
                    logger.info(f'Sending pushes for reminder {reminder.pk} for user {user.pk}')

                    push_tokens = list(UserPushToken.objects.filter(user=user).values_list('token', flat=True))

                    if len(push_tokens) > 0:
                        metricutils.increment('task', value=len(push_tokens), user=reminder.user,
                                              extra_tags=['name:reminder.queue.push'])

                        serializer = ReminderExtendedSerializer(reminder)
                        reminder_data = serializer.data

                        send_pushes.apply_async(
                            args=(push_tokens, user.username, subject, _push_body(reminder), reminder_data),
                            priority=settings.CELERY_PRIORITY_HIGH,
                        )
                    else:
                        logger.info(
                            f'Reminder {reminder.pk} was not pushed, as there are no active push tokens for user {user.pk}')
            else:
                logger.info(f"Marking reminder {reminder.pk} as sent without performing other actions")

            reminder.sent = True
            reminder.save()

            if reminder.repeating and reminder.course:
                _delete_excess_past_reminders(reminder)
                create_next_repeating_reminder(reminder)
        except Exception:
            logger.error("An error occurred processing push reminder.", exc_info=True)

        timezone.deactivate()
