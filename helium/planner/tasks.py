__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.utils import timezone

from conf.celery import app
from helium.common import enums
from helium.common.utils import commonutils
from helium.common.utils import metricutils
from helium.planner.models import Course, Category, Event, Homework
from helium.planner.models import Reminder
from helium.planner.services import gradingservice
from helium.planner.services import reminderservice

logger = logging.getLogger(__name__)


@app.task(bind=True)
def recalculate_course_group_grade(self, course_group_id, retries=0):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("grade.recalculate.course-group", priority="low", published_at_ms=published_at_ms)

    try:
        gradingservice.recalculate_course_group_grade(course_group_id)

        metricutils.task_stop(metrics, value=1)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_group_grade` task")

            recalculate_course_group_grade.apply_async(
                (course_group_id, retries + 1),
                countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS,
                priority=settings.CELERY_PRIORITY_LOW,
            )
            metricutils.task_stop(metrics, value=0)
        else:
            metricutils.task_failure('grade.recalculate.course-group', 'IntegrityError', priority="low")
            raise ex
    except ObjectDoesNotExist:
        logger.info(f"CourseGroup {course_group_id}, or an associated resource, does not exist. Nothing to do.")
        metricutils.task_stop(metrics, value=0)


@app.task(bind=True)
def recalculate_course_grade(self, course_id, retries=0):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("grade.recalculate.course", priority="low", published_at_ms=published_at_ms)

    try:
        course_group_id = Course.objects.select_related('course_group').get(pk=course_id).course_group.id

        gradingservice.recalculate_course_grade(course_id)

        recalculate_course_group_grade(course_group_id)

        metricutils.task_stop(metrics, value=1)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_course_grade` task")

            recalculate_course_grade.apply_async(
                (course_id, retries + 1),
                countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS,
                priority=settings.CELERY_PRIORITY_LOW,
            )
            metricutils.task_stop(metrics, value=0)
        else:
            metricutils.task_failure('grade.recalculate.course', 'IntegrityError', priority="low")
            raise ex
    except ObjectDoesNotExist:
        logger.info(f"Course {course_id}, or an associated resource, does not exist. Nothing to do.")
        metricutils.task_stop(metrics, value=0)


@app.task(bind=True)
def recalculate_course_grades_for_course_group(self, course_group_id):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("grade.recalculate.course-group-all", priority="low", published_at_ms=published_at_ms)

    count = 0
    for course_id in Course.objects.for_course_group(course_group_id).values_list("id", flat=True):
        recalculate_course_grade(course_id)
        count += 1

    metricutils.task_stop(metrics, value=count)


@app.task(bind=True)
def recalculate_category_grade(self, category_id, retries=0):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("grade.recalculate.category", priority="low", published_at_ms=published_at_ms)

    try:
        course_id = Category.objects.select_related('course').get(pk=category_id).course.id

        gradingservice.recalculate_category_grade(category_id)

        recalculate_course_grade(course_id)

        metricutils.task_stop(metrics, value=1)
    except IntegrityError as ex:  # pragma: no cover
        if retries < settings.DB_INTEGRITY_RETRIES:
            # This error is common when importing schedules, as async tasks may come in different orders
            logger.warning("Integrity error occurred, delaying before retrying `recalculate_category_grade` task")

            recalculate_category_grade.apply_async(
                (category_id, retries + 1),
                countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS,
                priority=settings.CELERY_PRIORITY_LOW,
            )
            metricutils.task_stop(metrics, value=0)
        else:
            metricutils.task_failure('grade.recalculate.category', 'IntegrityError', priority="low")
            raise ex
    except ObjectDoesNotExist:
        logger.info(f"Category {category_id}, or an associated resource, does not exist. Nothing to do.")
        metricutils.task_stop(metrics, value=0)


@app.task(bind=True)
def recalculate_category_grades_for_course(self, course_id):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("grade.recalculate.course-categories", priority="low", published_at_ms=published_at_ms)

    count = 0
    for category_id in Category.objects.for_course(course_id).values_list("id", flat=True):
        recalculate_category_grade(category_id)
        count += 1

    metricutils.task_stop(metrics, value=count)


@app.task(bind=True)
def adjust_reminder_times(self, calendar_item_id, calendar_item_type):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("reminder.adjust-times", priority="low", published_at_ms=published_at_ms)

    count = 0
    for reminder in (Reminder.objects
                     .for_calendar_item(calendar_item_id, calendar_item_type)
                     .select_related('homework', 'event', 'course')
                     .iterator()):
        logger.info(f'Adjusting start_of_range for reminder {reminder.pk}.')

        # Forcing a reminder to save will recalculate its start_of_range, if necessary
        reminder.save()
        count += 1

    metricutils.task_stop(metrics, value=count)


@app.task(bind=True)
def email_reminders(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("reminder.email.process", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Email reminders not being sent.')
        metricutils.task_stop(metrics, value=0)
        return

    reminderservice.process_email_reminders()
    metricutils.task_stop(metrics)


@app.task(bind=True)
def text_reminders(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("reminder.text.process", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_TEXTS:
        logger.warning('Texts disabled. Text reminders not being sent.')
        metricutils.task_stop(metrics, value=0)
        return

    reminderservice.process_text_reminders()
    metricutils.task_stop(metrics)


@app.task(bind=True)
def push_reminders(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("reminder.push.process", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_PUSH:
        logger.warning('Push disabled. Push reminders not being sent.')
        metricutils.task_stop(metrics, value=0)
        return

    reminderservice.process_push_reminders()
    metricutils.task_stop(metrics)


@app.task(bind=True)
def reminder_watchdog(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("reminder.watchdog", priority="low", published_at_ms=published_at_ms)

    reminderservice.heal_orphaned_repeating_reminders()
    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_email_reminder(self, email, subject, reminder_id, calendar_item_id, calendar_item_type):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.reminder.sent", priority="high", published_at_ms=published_at_ms)

    try:
        reminder = Reminder.objects.select_related('user', 'user__settings').get(pk=reminder_id)
    except Reminder.DoesNotExist:
        logger.info(f'Reminder {reminder_id} does not exist. Nothing to do.')
        metricutils.task_stop(metrics, value=0)
        return

    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Reminder {reminder.pk} not being sent.')
        metricutils.task_stop(metrics, value=0)
        return

    try:
        if calendar_item_type == enums.EVENT:
            calendar_item = Event.objects.get(pk=calendar_item_id)
        elif calendar_item_type == enums.HOMEWORK:
            calendar_item = Homework.objects.get(pk=calendar_item_id)
        elif calendar_item_type == enums.COURSE:
            calendar_item = Course.objects.prefetch_related('schedules').get(pk=calendar_item_id)
        else:
            logger.info(f'Nothing to do here, as a calendar_item_type of {calendar_item_type} does not exist.')
            metricutils.task_stop(metrics, value=0)
            return
    except (Event.DoesNotExist, Homework.DoesNotExist, Course.DoesNotExist):
        logger.info(f'calendar_item_id {calendar_item_id} does not exist. Nothing to do.')
        metricutils.task_stop(metrics, value=0)
        return

    timezone.activate(pytz.timezone(reminder.user.settings.time_zone))

    try:
        if calendar_item_type == enums.COURSE:
            from datetime import timedelta
            class_start = reminder.start_of_range + timedelta(
                **{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
            local_start = timezone.localtime(class_start)
            start_str = local_start.strftime(settings.NORMALIZED_DATE_TIME_FORMAT)

            weekday_idx = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[local_start.weekday()]
            day_name = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"][weekday_idx]
            active_schedule = next(
                (s for s in calendar_item.schedules.all() if s.days_of_week[weekday_idx] == "1"),
                None,
            )
            if active_schedule:
                end_time = getattr(active_schedule, f'{day_name}_end_time')
                end_str = local_start.replace(
                    hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0
                ).strftime('%I:%M %p')
                normalized_datetime = f'{start_str} to {end_str}'
            else:
                normalized_datetime = start_str

            comments = None
        else:
            start = timezone.localtime(calendar_item.start).strftime(
                settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
            end = timezone.localtime(calendar_item.end).strftime(
                settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
            normalized_datetime = f'{start} to {end}' if calendar_item.show_end_time else start

            comments = calendar_item.comments if calendar_item.comments.strip() != '' else None

        commonutils.send_multipart_email('email/reminder',
                                         {
                                             'PROJECT_NAME': settings.PROJECT_NAME,
                                             'reminder': reminder,
                                             'calendar_item': calendar_item,
                                             'normalized_datetime': normalized_datetime,
                                             'comments': comments,
                                             'notifications_url': f"{settings.PROJECT_APP_HOST}/notifications",
                                         },
                                         subject, [email],
                                         email_type='reminder')

        metricutils.task_stop(metrics, user=reminder.user)
    except Exception:
        logger.error("An error occurred sending email reminder.", exc_info=True)
        metricutils.task_stop(metrics, value=0)

    timezone.deactivate()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Process email reminders
    sender.add_periodic_task(60, email_reminders.s())

    # Process push reminders
    sender.add_periodic_task(60, push_reminders.s())

    # Process text reminders
    sender.add_periodic_task(60, text_reminders.s())

    sender.add_periodic_task(settings.REMINDER_WATCHDOG_FREQUENCY_SEC, reminder_watchdog.s().set(priority=settings.CELERY_PRIORITY_LOW))
