import logging

import pytz
from django.conf import settings
from django.utils import timezone

from helium.common import enums
from helium.common.utils import metricutils
from helium.planner.models import Reminder
from helium.common import tasks as commontasks
from helium.planner.tasks import remindertasks

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def get_subject(reminder):
    timezone.activate(pytz.timezone(reminder.user.settings.time_zone))

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
    for reminder in Reminder.reminders.with_type(enums.EMAIL).unsent().for_today().iterator():
        if reminder.user.email and reminder.user.is_active:
            subject = get_subject(reminder)

            if not subject:
                logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                continue

            if reminder.event:
                logger.info('Sending email reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.email')

                remindertasks.send_email_reminder.delay(reminder.email, subject, reminder, reminder.event)

            if reminder.homework:
                logger.info('Sending email reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.email')

                remindertasks.send_email_reminder.delay(reminder.email, subject, reminder, reminder.homework)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the phone and carrier are not longer set for user {}'.format(
                reminder.pk, reminder.user.pk))


def process_text_reminders():
    for reminder in Reminder.reminders.with_type(enums.TEXT).unsent().for_today().iterator():
        if reminder.user.profile.phone and reminder.user.profile.phone_carrier and reminder.user.profile.phone_verified:
            if reminder.event:
                subject = get_subject(reminder)
                message = '({}) {}'.format(subject, reminder.message)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending text reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.text')

                commontasks.send_text.delay(reminder.user.profile.phone, reminder.user.profile.phone_carrier,
                                            'Helium Reminder',
                                            message)

            if reminder.homework:
                subject = get_subject(reminder)
                message = '({}) {}'.format(subject, reminder.message)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending text reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.text')

                commontasks.send_text.delay(reminder.user.profile.phone, reminder.user.profile.phone_carrier,
                                            'Helium Reminder',
                                            message)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the phone and carrier are not longer set for user {}'.format(
                reminder.pk, reminder.user.pk))
