__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

import pytz
from django.conf import settings
from django.utils import timezone

from helium.auth.models.userpushtoken import UserPushToken
from helium.common import enums
from helium.common.tasks import send_text, send_pushes
from helium.common.utils import metricutils
from helium.planner.models import Reminder
from helium.planner.serializers.reminderserializer import ReminderExtendedSerializer

logger = logging.getLogger(__name__)


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


def create_next_repeating_reminder(reminder):
    """
    For a repeating reminder (course), create the next occurrence.
    """
    if not reminder.repeating or not reminder.course:
        return None

    # Create a new reminder with the same settings
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

    # Check if there's a next occurrence (save() will calculate start_of_range)
    next_start = new_reminder._get_next_course_occurrence_start()
    if next_start:
        new_reminder.save()
        return new_reminder

    return None


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

            # Create next reminder if this is a repeating reminder
            if reminder.repeating:
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
                message = f'({subject}) {reminder.message}'

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

            # Create next reminder if this is a repeating reminder
            if reminder.repeating:
                create_next_repeating_reminder(reminder)
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
                            args=(push_tokens, user.username, subject, reminder.message, reminder_data),
                            priority=settings.CELERY_PRIORITY_HIGH,
                        )
                    else:
                        logger.info(
                            f'Reminder {reminder.pk} was not pushed, as there are no active push tokens for user {user.pk}')
            else:
                logger.info(f"Marking reminder {reminder.pk} as sent without performing other actions")

            reminder.sent = True
            reminder.save()

            # Create next reminder if this is a repeating reminder
            if reminder.repeating:
                create_next_repeating_reminder(reminder)
        except Exception:
            logger.error("An error occurred processing push reminder.", exc_info=True)

        timezone.deactivate()
