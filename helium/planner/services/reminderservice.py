__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

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
        timezone.activate(pytz.timezone(reminder.get_user().settings.time_zone))

        if reminder.get_user().email and reminder.get_user().is_active:
            subject = get_subject(reminder)

            if not subject:
                logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned.')
                continue

            if reminder.event:
                calendar_item_id = reminder.event.pk
                calendar_item_type = enums.EVENT
            elif reminder.homework:
                calendar_item_id = reminder.homework.pk
                calendar_item_type = enums.HOMEWORK
            else:
                logger.warning(f'Reminder {reminder.pk} was not for a homework or event. Nothing to do.')
                continue

            logger.info(f'Sending email reminder {reminder.pk} for user {reminder.get_user().pk}')

            metricutils.increment('task.reminder.queue.email')

            send_email_reminder.delay(reminder.get_user().email, subject, reminder.pk, calendar_item_id,
                                      calendar_item_type)
        else:
            logger.warning(
                f'Reminder {reminder.pk} was not processed, as the account appears to be inactive for user {reminder.get_user().pk}')

        reminder.sent = True
        reminder.save()

        timezone.deactivate()


def process_text_reminders():
    for reminder in Reminder.objects.with_type(enums.TEXT).unsent().for_today().iterator():
        timezone.activate(pytz.timezone(reminder.get_user().settings.time_zone))

        if reminder.get_user().profile.phone and reminder.get_user().profile.phone_verified:
            subject = get_subject(reminder)
            message = f'({subject}) {reminder.message}'

            if not subject:
                logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
                continue

            logger.info(f'Sending text reminder {reminder.pk} for user {reminder.get_user().pk}')

            metricutils.increment('task.reminder.queue.text')

            send_text.delay(reminder.get_user().profile.phone,
                            message)
        else:
            logger.warning(
                f'Reminder {reminder.pk} was not processed, as the phone and carrier are no longer set for user {reminder.get_user().pk}')

        reminder.sent = True
        reminder.save()

        timezone.deactivate()


def process_push_reminders():
    for reminder in Reminder.objects.with_type(enums.PUSH).unsent().for_today().iterator():
        timezone.activate(pytz.timezone(reminder.get_user().settings.time_zone))

        subject = get_subject(reminder)
        message = f'({subject}) {reminder.message}'

        if not subject:
            logger.warning(f'Reminder {reminder.pk} was not processed, as it appears to be orphaned')
            continue

        logger.info(f'Sending pushes for reminder {reminder.pk} for user {reminder.get_user().pk}')

        push_tokens = UserPushToken.objects.filter(user=reminder.get_user()).values_list('token', flat=True)

        if len(push_tokens) > 0:
            metricutils.increment('task.reminder.queue.push', len(push_tokens))

            send_pushes.delay(push_tokens,
                              subject,
                              message)
        else:
            logger.warning(
                f'Reminder {reminder.pk} was not processed, as the phone and carrier are no longer set for user {reminder.get_user().pk}')

        reminder.sent = True
        reminder.save()

        timezone.deactivate()
