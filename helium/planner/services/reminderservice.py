import logging

import pytz
from django.conf import settings
from django.utils import timezone

from helium.common import enums
from helium.common.tasks import send_text
from helium.common.utils import metricutils
from helium.planner.models import Reminder

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


def get_subject(reminder):
    if reminder.homework:
        calendar_item = reminder.homework
        subject = '{} in {}'.format(calendar_item.title, calendar_item.course.title)
    elif reminder.event:
        calendar_item = reminder.event
        subject = calendar_item.title
    else:
        return

    start = timezone.localtime(calendar_item.start).strftime(
        settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
    subject += ' on {}'.format(start)

    return subject


def process_email_reminders():
    from helium.planner.tasks import send_email_reminder

    for reminder in Reminder.objects.with_type(enums.EMAIL).unsent().for_today().iterator():
        if reminder.get_user().email and reminder.get_user().is_active:
            subject = get_subject(reminder)

            if not subject:
                logger.warn('Reminder {} was not processed, as it appears to be orphaned.'.format(reminder.pk))
                continue

            if reminder.event:
                calendar_item_id = reminder.event.pk
                calendar_item_type = enums.EVENT
            elif reminder.homework:
                calendar_item_id = reminder.homework.pk
                calendar_item_type = enums.HOMEWORK
            else:
                logger.warn('Reminder {} was not for a homework or event. Nothing to do.'.format(reminder.pk))
                continue

            logger.info('Sending email reminder {} for user {}'.format(reminder.pk, reminder.get_user().pk))

            metricutils.increment('task.reminder.queue.email')

            send_email_reminder.delay(reminder.get_user().email, subject, reminder.pk, calendar_item_id,
                                      calendar_item_type)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the account appears to be inactive for user {}'.format(
                reminder.pk, reminder.get_user().pk))


def process_text_reminders():
    for reminder in Reminder.objects.with_type(enums.TEXT).unsent().for_today().iterator():
        timezone.activate(pytz.timezone(reminder.get_user().settings.time_zone))

        if reminder.get_user().profile.phone and reminder.get_user().profile.phone_carrier and reminder.get_user().profile.phone_verified:
            subject = get_subject(reminder)
            message = '({}) {}'.format(subject, reminder.message)

            if not subject:
                logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                continue

            logger.info('Sending text reminder {} for user {}'.format(reminder.pk, reminder.get_user().pk))

            metricutils.increment('task.reminder.queue.text')

            send_text.delay(reminder.get_user().profile.phone,
                            reminder.get_user().profile.phone_carrier,
                            'Helium Reminder',
                            message)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the phone and carrier are no longer set for user {}'.format(
                reminder.pk, reminder.get_user().pk))

        timezone.deactivate()
