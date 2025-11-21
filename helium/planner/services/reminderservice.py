__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.14.7"

import logging

import pytz
from django.conf import settings
from django.utils import timezone

from helium.auth.models.userpushtoken import UserPushToken
from helium.common import enums
from helium.common.tasks import send_text, send_pushes
from helium.common.utils import metricutils
from helium.planner.models import Reminder

logger = logging.getLogger(__name__)


def get_subject(reminder):
    if reminder.homework:
        calendar_item = reminder.homework
        subject = f'{calendar_item.title} in {calendar_item.course.title}'
    elif reminder.event:
        calendar_item = reminder.event
        subject = calendar_item.title
    else:
        return

    start = timezone.localtime(calendar_item.start).strftime(
        settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
    subject += f' on {start}'

    return subject


def process_email_reminders():
    from helium.planner.tasks import send_email_reminder

    for reminder in Reminder.objects.with_type(enums.EMAIL).unsent().for_today().iterator():
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
                    else:
                        logger.warning(f'Reminder {reminder.pk} was not for a homework or event. Nothing to do.')
                        continue

                    logger.info(f'Sending email reminder {reminder.pk} for user {user.pk}')

                    metricutils.increment('task', user=user, extra_tags=['name:reminder.queue.email'])

                    send_email_reminder.delay(user.email, subject, reminder.pk, calendar_item_id, calendar_item_type)
            else:
                logger.warning(
                    f'Reminder {reminder.pk} was not processed, as the account appears to be inactive for user {user.pk}')

            reminder.sent = True
            reminder.save()
        except:
            logger.error("An unknown error occurred.", exc_info=True)

        timezone.deactivate()


def process_text_reminders():
    for reminder in Reminder.objects.with_type(enums.TEXT).unsent().for_today().iterator():
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

                    send_text.delay(user.profile.phone, message)
            else:
                logger.warning(
                    f'Reminder {reminder.pk} was not processed, as the phone and carrier are no longer set for user {user.pk}')

            reminder.sent = True
            reminder.save()
        except:
            logger.error("An unknown error occurred.", exc_info=True)

        timezone.deactivate()


def process_push_reminders(mark_sent_only=False):
    for reminder in Reminder.objects.with_type(enums.POPUP).unsent().for_today().iterator():
        user = reminder.get_user()

        timezone.activate(pytz.timezone(user.settings.time_zone))

        try:
            if not mark_sent_only:
                subject = get_subject(reminder)

                if not subject:
                    logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
                else:
                    logger.info(f'Sending pushes for reminder {reminder.pk} for user {user.pk}')

                    push_tokens = list(UserPushToken.objects.filter(user=user).values_list('token', flat=True))

                    if len(push_tokens) > 0:
                        metricutils.increment('task', value=len(push_tokens), user=reminder.user, extra_tags=['name:reminder.queue.push'])

                        send_pushes.delay(push_tokens, user.username, subject, reminder.message)
                    else:
                        logger.warning(
                            f'Reminder {reminder.pk} was not pushed, as there are no active push tokens for user {user.pk}')
            else:
                logger.info(f"Marking reminder {reminder.pk} as sent without performing other actions")

            reminder.sent = True
            reminder.save()
        except:
            logger.error("An unknown error occurred.", exc_info=True)

        timezone.deactivate()
