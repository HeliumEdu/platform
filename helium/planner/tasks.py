__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
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

logger = logging.getLogger(__name__)


@app.task
def recalculate_course_group_grade(course_group_id, retries=0):

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course_group = CourseGroup.objects.get(pk=course_group_id)

        metricutils.increment('task.grading.recalculate.course-group', user=course_group.user)
        gradingservice.recalculate_course_group_grade(course_group)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_group_grade` task")

            recalculate_course_group_grade.apply_async((course_group_id, retries + 1),
                                                       countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS)
        else:
            raise ex
    except get_user_model().DoesNotExist:
        logger.info(f"User does not exist. Nothing to do.")
    except CourseGroup.DoesNotExist:
        logger.info(f"CourseGroup {course_group_id} does not exist. Nothing to do.")


@app.task
def recalculate_course_grade(course_id, retries=0):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        metricutils.increment('task.grading.recalculate.course', user=course.get_user())

        gradingservice.recalculate_course_grade(course)

        recalculate_course_group_grade(course.course_group.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_grade` task")

            recalculate_course_grade.apply_async((course_id, retries + 1),
                                                 countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS)
        else:
            raise ex
    except get_user_model().DoesNotExist:
        logger.info(f"User does not exist. Nothing to do.")
    except Course.DoesNotExist:
        logger.info(f"Course {course_id} does not exist. Nothing to do.")


@app.task
def recalculate_category_grades_for_course(course_id, retries=0):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        course = Course.objects.get(pk=course_id)

        for category in course.categories.iterator():
            recalculate_category_grade(category.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning(
                "Integrity error occurred, delaying before retrying `recalculate_category_grades_for_course` task")

            recalculate_category_grades_for_course.apply_async((course_id, retries + 1),
                                                               countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS)
        else:
            raise ex
    except Course.DoesNotExist:
        logger.info(f"Course {course_id} does not exist. Nothing to do.")


@app.task
def recalculate_category_grade(category_id, retries=0):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        category = Category.objects.get(pk=category_id)

        metricutils.increment('task.grading.recalculate.category', user=category.get_user())

        gradingservice.recalculate_category_grade(category)

        recalculate_course_grade(category.course.pk)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_category_grade` task")

            recalculate_category_grade.apply_async((category_id, retries + 1),
                                                   countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS)
        else:
            raise ex
    except get_user_model().DoesNotExist:
        logger.info(f"User does not exist. Nothing to do.")
    except Category.DoesNotExist:
        logger.info(f"Category {category_id} does not exist. Nothing to do.")


@app.task
def adjust_reminder_times(calendar_item_id, calendar_item_type):
    for reminder in Reminder.objects.for_calendar_item(calendar_item_id, calendar_item_type).iterator():
        logger.info(f'Adjusting start_of_range for reminder {reminder.pk}.')

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
    if settings.DISABLE_TEXTS:
        logger.warning('Texts disabled. Text reminders not being sent.')
        return

    reminderservice.process_text_reminders()


@app.task
def push_reminders():
    if settings.DISABLE_PUSH:
        logger.warning('Push disabled. Text reminders not being sent.')
        return

    reminderservice.process_push_reminders()


@app.task
def send_email_reminder(email, subject, reminder_id, calendar_item_id, calendar_item_type):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        reminder = Reminder.objects.get(pk=reminder_id)
    except Reminder.DoesNotExist:
        logger.info(f'Reminder {reminder_id} does not exist. Nothing to do.')

        return

    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Reminder {reminder.pk} not being sent.')
        return

    try:
        if calendar_item_type == enums.EVENT:
            calendar_item = Event.objects.get(pk=calendar_item_id)
        elif calendar_item_type == enums.HOMEWORK:
            calendar_item = Homework.objects.get(pk=calendar_item_id)
        else:
            logger.info(f'Nothing to do here, as a calendar_item_type of {calendar_item_type} does not exist.')

            return
    except (Event.DoesNotExist, Homework.DoesNotExist):
        logger.info(f'calendar_item_id {calendar_item_id} does not exist. Nothing to do.')

        return

    timezone.activate(pytz.timezone(reminder.user.settings.time_zone))

    try:
        start = timezone.localtime(calendar_item.start).strftime(
            settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
        end = timezone.localtime(calendar_item.end).strftime(
            settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
        normalized_datetime = f'{start} to {end}' if calendar_item.show_end_time else start

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

        metricutils.increment('task.email.reminder.sent', user=reminder.user)
    except:
        logger.error("An unknown error occurred.", exc_info=True)

    timezone.deactivate()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule for email reminders periodically
    sender.add_periodic_task(settings.REMINDERS_FREQUENCY_SEC, email_reminders.s())

    # Add schedule for text reminders periodically
    sender.add_periodic_task(settings.REMINDERS_FREQUENCY_SEC, text_reminders.s())
