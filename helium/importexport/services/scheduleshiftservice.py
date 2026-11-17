import datetime
import logging
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from helium.common.utils import datetimeutils
from helium.common.utils.datetimeutils import local_midnight_as_utc
from helium.common.utils.validators import shift_recurrence_rule_for_user
from helium.common.utils.course_exception_helpers import get_course_exceptions, get_course_group_exceptions
from helium.planner.models import CourseGroup, Course, Homework, Event, Reminder
from helium.planner.services import coursescheduleservice
from helium.planner.services import reminderservice
from helium.planner.tasks import adjust_reminder_times

logger = logging.getLogger(__name__)


def _shift_datetime_to_target_date(original_dt, target_date, target_tz, all_day=False, source_tz=None):
    """
    Move a datetime onto `target_date`, translating the wall clock it reads in `source_tz` into
    `target_tz`, so an 11:00 example item is 11:00 for everyone. Reads in `target_tz` when no source
    is given. All-day items have no wall clock, so they land on midnight in `target_tz`.

    :param original_dt: The original aware datetime (in UTC)
    :param all_day: If True, use midnight instead of preserving wall-clock time
    :return: New aware datetime in UTC
    """
    if all_day:
        return local_midnight_as_utc(target_date, target_tz)

    local_dt = original_dt.astimezone(source_tz or target_tz)
    naive_target = datetime.datetime(
        target_date.year, target_date.month, target_date.day,
        local_dt.hour, local_dt.minute, 0, 0
    )

    aware_target = naive_target.replace(tzinfo=target_tz)
    return aware_target.astimezone(datetime.timezone.utc)


def _get_most_recent_course_occurrence_start(reminder):
    """
    Calculate the most recent past occurrence start time for a course reminder.
    Walks backward from today to find the last class session that already happened.
    """
    course = reminder.course
    course_schedules = list(course.schedules.all())
    if not course_schedules:
        return None

    user_tz = ZoneInfo(course.get_user().settings.time_zone)
    now = datetime.datetime.now(user_tz)
    today = now.date()

    exceptions = get_course_exceptions(course)
    group_exceptions = get_course_group_exceptions(course)
    day = min(today, course.end_date)

    while day >= course.start_date:
        if day in exceptions:
            day -= datetime.timedelta(days=1)
            continue

        # Multiple schedules can meet the same day (lecture + lab, or a cycle-day slot) — take the latest.
        candidates = []
        for course_schedule in course_schedules:
            for start_time, _end_time in coursescheduleservice.schedule_meeting_times_for_day(
                    course_schedule, day, exceptions, group_exceptions):
                local_start = datetime.datetime.combine(day, start_time).replace(tzinfo=user_tz)

                if local_start <= now:
                    candidates.append(local_start)

        if candidates:
            return max(candidates).astimezone(datetime.timezone.utc)

        day -= datetime.timedelta(days=1)

    return None


def _days_until_monday(dt):
    days_ahead = 0 - dt.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return days_ahead


def shift_schedule_to_month(user, adjust_month, imported, source_tz=None):
    user_tz = ZoneInfo(user.settings.time_zone)
    timezone.activate(user_tz)

    now = timezone.now().astimezone(user_tz)
    years_ahead, month_index = divmod(now.month - 1 + adjust_month, 12)
    adjusted_year = now.year + years_ahead
    adjusted_month = month_index + 1

    try:
        # Savepoint so a failure here can't poison import_example_schedule's outer transaction.
        with transaction.atomic():
            adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0, second=0,
                                         microsecond=0)
            days_ahead = _days_until_monday(adjusted_month)
            first_monday = adjusted_month + datetime.timedelta(days_ahead)
            first_monday_date = first_monday.date()

            logger.info(f'Adjusting schedule relative to new month: {adjusted_month}')
            logger.info(f'Start of week adjusted ahead {days_ahead} days')
            logger.info(f'First Monday set to {first_monday}')

            course_groups_to_update = []
            for course_group in (CourseGroup.objects.for_user(user.pk)
                    .filter(pk__in=imported.course_group_remap.values())):
                delta = (course_group.end_date - course_group.start_date).days
                course_group.start_date = first_monday_date
                course_group.end_date = first_monday_date + datetime.timedelta(days=delta)
                course_groups_to_update.append(course_group)

            if course_groups_to_update:
                CourseGroup.objects.bulk_update(course_groups_to_update, ['start_date', 'end_date'])

            homework_to_update = []
            for homework in (Homework.objects.for_user(user.pk)
                    .filter(pk__in=imported.homework_remap.values())
                    .select_related('course')):
                course = homework.course
                start_delta = (homework.start.date() - course.start_date).days
                end_delta = (homework.end.date() - course.start_date).days
                target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
                target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

                original_start = homework.start
                homework.start = _shift_datetime_to_target_date(homework.start, target_start_date, user_tz,
                                                                 all_day=homework.all_day, source_tz=source_tz)
                homework.end = _shift_datetime_to_target_date(homework.end, target_end_date, user_tz,
                                                               all_day=homework.all_day, source_tz=source_tz)
                if homework.recurrence_rule:
                    homework.recurrence_rule = shift_recurrence_rule_for_user(
                        homework.recurrence_rule, original_start, homework.start, user)
                    homework.exception_dates = datetimeutils.shift_exception_dates(
                        homework.exception_dates, original_start, homework.start, user_tz)
                homework_to_update.append(homework)

            if homework_to_update:
                Homework.objects.bulk_update(homework_to_update, ['start', 'end', 'recurrence_rule', 'exception_dates'])
                hw_ids_with_reminders = set(
                    Reminder.objects.filter(homework__in=[h.pk for h in homework_to_update])
                    .values_list('homework_id', flat=True).distinct()
                )
                for homework in homework_to_update:
                    if homework.pk in hw_ids_with_reminders:
                        adjust_reminder_times(homework.pk, homework.calendar_item_type)

            first_event_start = Event.objects.for_user(user.pk).filter(
                pk__in=imported.event_remap.values()).first().start

            first_event_month = first_event_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            days_ahead = _days_until_monday(first_event_month)
            first_event_monday = first_event_month + datetime.timedelta(days_ahead)
            events_delta = (first_monday - first_event_monday).days

            events_to_update = []
            for event in (Event.objects.for_user(user.pk)
                    .filter(pk__in=imported.event_remap.values())):
                start_delta = (event.start.date() - first_monday.date()).days + events_delta
                end_delta = (event.end.date() - first_monday.date()).days + events_delta
                target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
                target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

                original_start = event.start
                event.start = _shift_datetime_to_target_date(event.start, target_start_date, user_tz,
                                                              all_day=event.all_day, source_tz=source_tz)
                event.end = _shift_datetime_to_target_date(event.end, target_end_date, user_tz,
                                                            all_day=event.all_day, source_tz=source_tz)
                if event.recurrence_rule:
                    event.recurrence_rule = shift_recurrence_rule_for_user(
                        event.recurrence_rule, original_start, event.start, user)
                    event.exception_dates = datetimeutils.shift_exception_dates(
                        event.exception_dates, original_start, event.start, user_tz)
                events_to_update.append(event)

            if events_to_update:
                Event.objects.bulk_update(events_to_update, ['start', 'end', 'recurrence_rule', 'exception_dates'])
                event_ids_with_reminders = set(
                    Reminder.objects.filter(event__in=[e.pk for e in events_to_update])
                    .values_list('event_id', flat=True).distinct()
                )
                for event in events_to_update:
                    if event.pk in event_ids_with_reminders:
                        adjust_reminder_times(event.pk, event.calendar_item_type)

            courses_to_update = []
            for course in (Course.objects.for_user(user.pk)
                    .filter(pk__in=imported.course_remap.values())
                    .select_related('course_group')):
                delta = (course.end_date - course.start_date).days
                course.start_date = first_monday_date
                course.end_date = first_monday_date + datetime.timedelta(days=delta)
                courses_to_update.append(course)

            if courses_to_update:
                Course.objects.bulk_update(courses_to_update, ['start_date', 'end_date'])

            for course in courses_to_update:
                coursescheduleservice.clear_cached_course_schedule(course)

            for reminder in (Reminder.objects
                    .filter(course_id__in=imported.course_remap.values(), sent=True, user=user)
                    .select_related('user', 'user__settings', 'course', 'course__course_group')
                    .prefetch_related('course__schedules')
                    .iterator(chunk_size=2000)):
                past_start = _get_most_recent_course_occurrence_start(reminder)
                if past_start:
                    offset_delta = datetimeutils.offset_to_timedelta(reminder.offset, reminder.offset_type)
                    Reminder.objects.filter(pk=reminder.pk).update(
                        start_of_range=past_start - offset_delta)

                reminderservice.create_next_repeating_reminder(reminder)

            logger.info(
                f'Dates adjusted on imported example schedule relative to the start of the month for new user {user.pk}')
    except Exception:
        logger.error("An error occurred adjusting example schedule dates.", exc_info=True)

    timezone.deactivate()
