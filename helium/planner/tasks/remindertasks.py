import logging

import pytz
from celery.schedules import crontab
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.utils import timezone

from conf.celery import app
from helium.common import enums
from helium.common import tasks
from helium.common.utils import metricutils
from helium.planner.models import Reminder
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

    for reminder in Reminder.reminders.with_type(enums.EMAIL).unsent().for_today().iterator():
        if reminder.user.email and reminder.user.is_active:
            if reminder.event:
                subject = reminderservice.get_subject(reminder)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending email reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.email')

                send_email_reminder.delay(reminder.email, subject, reminder, reminder.event)

            if reminder.homework:
                subject = reminderservice.get_subject(reminder)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending email reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.email')

                send_email_reminder.delay(reminder.email, subject, reminder, reminder.homework)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the phone and carrier are not longer set for user {}'.format(
                reminder.pk, reminder.user.pk))


@app.task
def text_reminders():
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Text reminders not being sent.')
        return

    for reminder in Reminder.reminders.with_type(enums.TEXT).unsent().for_today().iterator():
        if reminder.user.profile.phone and reminder.user.profile.phone_carrier and reminder.user.profile.phone_verified:
            if reminder.event:
                subject = reminderservice.get_subject(reminder)
                message = '({}) {}'.format(subject, reminder.message)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending text reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.text')

                tasks.send_text.delay(reminder.user.profile.phone, reminder.user.profile.phone_carrier,
                                      'Helium Reminder',
                                      message)

            if reminder.homework:
                subject = reminderservice.get_subject(reminder)
                message = '({}) {}'.format(subject, reminder.message)

                if not subject:
                    logger.warn('Reminder {} was not processed, as it appears to be orphaned'.format(reminder.pk))
                    continue

                logger.info('Sending text reminder {} for user {}'.format(reminder.pk, reminder.user.pk))

                metricutils.increment('task.reminder.queue.text')

                tasks.send_text.delay(reminder.user.profile.phone, reminder.user.profile.phone_carrier,
                                      'Helium Reminder',
                                      message)

            reminder.sent = True
            reminder.save()
        else:
            logger.warn('Reminder {} was not processed, as the phone and carrier are not longer set for user {}'.format(
                reminder.pk, reminder.user.pk))


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

    plaintext = get_template('email/reminder.txt')
    html = get_template('email/reminder.html')
    c = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'reminder': reminder,
        'calendar_item': calendar_item,
        'normalized_datetime': normalized_datetime,
        'normalized_materials': normalized_materials,
        'comments': calendar_item.comments if calendar_item.comments.strip() != '' else None,
        'site_url': settings.PLATFORM_HOST,
    }
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Email reminders every minute
    sender.add_periodic_task(crontab(), email_reminders.s())

    # Text reminders every minute
    sender.add_periodic_task(crontab(), text_reminders.s())
