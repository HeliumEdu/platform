import logging

import pytz
from celery.schedules import crontab
from django.conf import settings
from django.utils import timezone

from conf.celery import app
from helium.common.utils import commonutils
from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.models import Reminder
from helium.planner.services import gradingservice
from helium.planner.services import reminderservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group_id):
    metricutils.increment('task.grading.recalculate.course-group')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        gradingservice.recalculate_course_group_grade(CourseGroup.objects.get(pk=course_group_id))
    except Category.DoesNotExist:
        pass


@app.task
def recalculate_course_grade(course_id):
    metricutils.increment('task.grading.recalculate.course')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        gradingservice.recalculate_course_grade(course)

        recalculate_course_group_grade.delay(course.course_group.pk)
    except Course.DoesNotExist:
        pass


@app.task
def recalculate_category_grade(category_id):
    metricutils.increment('task.grading.recalculate.category')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        category = Category.objects.get(pk=category_id)

        gradingservice.recalculate_category_grade(category)

        recalculate_course_grade.delay(category.course.pk)
    except Category.DoesNotExist:
        pass


@app.task
def adjust_reminder_times(calendar_item_id, calendar_item_type):
    for reminder in Reminder.objects.for_calendar_item(calendar_item_id, calendar_item_type).iterator():
        logger.info('Adjusting start_of_range for reminder {}.'.format(reminder.pk))

        # Forcing a reminder to save will recalculate its start_of_range, if necessary
        reminder.save()


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
def send_email_reminder(email, subject, reminder_id, calendar_item):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        reminder = Reminder.objects.get(pk=reminder_id)
    except Reminder.DoesNotExist:
        return

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


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # Add schedule for email reminders every minute
    sender.add_periodic_task(crontab(), email_reminders.s())

    # Add schedule for text reminders every minute
    sender.add_periodic_task(crontab(), text_reminders.s())
