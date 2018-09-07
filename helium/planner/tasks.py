import logging

import pytz
from django.conf import settings
from django.db import IntegrityError
from django.utils import timezone

from conf.celery import app
from helium.common import enums
from helium.common.utils import commonutils
from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course, Category, Event, Homework
from helium.planner.models import Reminder
from helium.planner.services import gradingservice
from helium.planner.services import reminderservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.33'

logger = logging.getLogger(__name__)

_INTEGRITY_RETRIES = 2
_INTEGRITY_RETRY_DELAY = 2


@app.task
def recalculate_course_group_grade(course_group_id, retries=0):
    metricutils.increment('task.grading.recalculate.course-group')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        gradingservice.recalculate_course_group_grade(CourseGroup.objects.get(pk=course_group_id))
    except IntegrityError as ex:  # pragma: no cover
        if retries < _INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_group_grade` task")

            recalculate_course_group_grade.apply_async((course_group_id, retries + 1), countdown=_INTEGRITY_RETRY_DELAY)
        else:
            raise ex
    except CourseGroup.DoesNotExist:
        logger.info("CourseGroup {} does not exist. Nothing to do.".format(course_group_id))


@app.task
def recalculate_course_grade(course_id, retries=0):
    metricutils.increment('task.grading.recalculate.course')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        gradingservice.recalculate_course_grade(course)

        recalculate_course_group_grade(course.course_group.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < _INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_grade` task")

            recalculate_course_grade.apply_async((course_id, retries + 1), countdown=_INTEGRITY_RETRY_DELAY)
        else:
            raise ex
    except Course.DoesNotExist:
        logger.info("Course {} does not exist. Nothing to do.".format(course_id))


@app.task
def recalculate_category_grades_for_course(course_id, retries=0):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        for category in course.categories.iterator():
            recalculate_category_grade(category.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < _INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning(
                "Integrity error occurred, delaying before retrying `recalculate_category_grades_for_course` task")

            recalculate_category_grades_for_course.apply_async((course_id, retries + 1),
                                                               countdown=_INTEGRITY_RETRY_DELAY)
        else:
            raise ex
    except Course.DoesNotExist:
        logger.info("Course {} does not exist. Nothing to do.".format(course_id))


@app.task
def recalculate_category_grade(category_id, retries=0):
    metricutils.increment('task.grading.recalculate.category')

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        category = Category.objects.get(pk=category_id)

        gradingservice.recalculate_category_grade(category)

        recalculate_course_grade(category.course.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < _INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_category_grade` task")

            recalculate_category_grade.apply_async((category_id, retries + 1), countdown=_INTEGRITY_RETRY_DELAY)
        else:
            raise ex
    except Category.DoesNotExist:
        logger.info("Category {} does not exist. Nothing to do.".format(category_id))


@app.task
def adjust_reminder_times(calendar_item_id, calendar_item_type):
    for reminder in Reminder.objects.for_calendar_item(calendar_item_id, calendar_item_type).iterator():
        logger.info('Adjusting start_of_range for reminder {}.'.format(reminder.pk))

        # Forcing a reminder to save will recalculate its start_of_range, if necessary
        reminder.save()


@app.task
def email_reminders():
    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Email reminders not being sent.')
        return

    reminderservice.process_email_reminders()


@app.task
def text_reminders():
    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Text reminders not being sent.')
        return

    reminderservice.process_text_reminders()


@app.task
def send_email_reminder(email, subject, reminder_id, calendar_item_id, calendar_item_type):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        reminder = Reminder.objects.get(pk=reminder_id)
    except Reminder.DoesNotExist:
        logger.info('Reminder {} does not exist. Nothing to do.'.format(reminder_id))

        return

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Reminder {} not being sent.'.format(reminder.pk))
        return

    try:
        if calendar_item_type == enums.EVENT:
            calendar_item = Event.objects.get(pk=calendar_item_id)
        elif calendar_item_type == enums.HOMEWORK:
            calendar_item = Homework.objects.get(pk=calendar_item_id)
        else:
            logger.info('Nothing to do here, as a calendar_item_type of {} does not exist.'.format(calendar_item_type))

            return
    except (Event.DoesNotExist, Homework.DoesNotExist):
        logger.info('calendar_item_id {} does not exist. Nothing to do.'.format(calendar_item_id))

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

    comments = calendar_item.comments if calendar_item.comments.strip() != '' else None

    commonutils.send_multipart_email('email/reminder',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'reminder': reminder,
                                         'calendar_item': calendar_item,
                                         'normalized_datetime': normalized_datetime,
                                         'normalized_materials': normalized_materials,
                                         'comments': comments,
                                     },
                                     subject, [email])

    metricutils.increment('action.reminder.sent.email')

    timezone.deactivate()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule for email reminders every ten seconds
    sender.add_periodic_task(10.0, email_reminders.s())

    # Add schedule for text reminders every ten seconds
    sender.add_periodic_task(10.0, text_reminders.s())
