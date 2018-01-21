import logging

import pytz
from celery.schedules import crontab
from django.conf import settings
from django.utils import timezone

from conf.celery import app
from helium.common.utils import commonutils
from helium.planner.services import reminderservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def email_reminders():
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Email reminders not being sent.')
        return

    reminderservice.process_email_reminders()


@app.task
def text_reminders():
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Text reminders not being sent.')
        return

    reminderservice.process_text_reminders()


@app.task
def send_email_reminder(email, subject, reminder, calendar_item):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Reminder {} not being sent.'.format(reminder.pk))
        return

    timezone.activate(pytz.timezone(reminder.user.settings.time_zone))

    start = timezone.localtime(calendar_item.start).strftime(
        settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
    end = timezone.localtime(calendar_item.end).strftime(
        settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
    normalized_datetime = '{} to {}'.format(start, end) if calendar_item.show_end_time else start

    normalized_materials = None
    if reminder.homework:
        normalized_materials = calendar_item.materials.values_list('title', flat=True)
        normalized_materials = ', '.join(normalized_materials)

    commonutils.send_multipart_email('email/reminder',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'reminder': reminder,
                                         'calendar_item': calendar_item,
                                         'normalized_datetime': normalized_datetime,
                                         'normalized_materials': normalized_materials,
                                         'comments': calendar_item.comments if calendar_item.comments.strip() != '' else None,
                                         'site_url': settings.PLATFORM_HOST,
                                     },
                                     subject, [email])


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Email reminders every minute
    sender.add_periodic_task(crontab(), email_reminders.s())

    # Text reminders every minute
    sender.add_periodic_task(crontab(), text_reminders.s())
