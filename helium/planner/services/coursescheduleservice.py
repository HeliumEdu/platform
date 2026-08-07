__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import logging
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from dateutil import parser
from django.conf import settings
from django.core.cache import cache

from helium.common import enums
from helium.common.utils import metricutils
from helium.common.utils.commonutils import HeliumError, deterministic_id
from helium.common.utils.course_exception_helpers import get_course_exceptions
from helium.common.utils.validators import WEEKDAY_TO_ICAL
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import EventSerializer

logger = logging.getLogger(__name__)

_SUNDAY = 0
_MONDAY = 1
_TUESDAY = 2
_WEDNESDAY = 3
_THURSDAY = 4
_FRIDAY = 5
_SATURDAY = 6

_HELIUM_TO_PYTHON_WEEKDAY = {helium: python for python, helium in enums.PYTHON_TO_HELIUM_DAY_OF_WEEK.items()}


class HeliumCourseScheduleError(HeliumError):
    pass


def _get_start_time_for_weekday(course_schedule, weekday):
    if _SUNDAY < weekday > _SATURDAY:
        raise HeliumCourseScheduleError(f'"{weekday}" is an invalid weekday value. Allowed values are [0-6].')

    if course_schedule.days_of_week[weekday] != "1":
        return None

    if weekday == _SUNDAY:
        return course_schedule.sun_start_time
    elif weekday == _MONDAY:
        return course_schedule.mon_start_time
    elif weekday == _TUESDAY:
        return course_schedule.tue_start_time
    elif weekday == _WEDNESDAY:
        return course_schedule.wed_start_time
    elif weekday == _THURSDAY:
        return course_schedule.thu_start_time
    elif weekday == _FRIDAY:
        return course_schedule.fri_start_time
    elif weekday == _SATURDAY:
        return course_schedule.sat_start_time


def _get_end_time_for_weekday(course_schedule, weekday):
    if _SUNDAY < weekday > _SATURDAY:
        raise HeliumCourseScheduleError(f'"{weekday}" is an invalid weekday value. Allowed values are [0-6].')

    if course_schedule.days_of_week[weekday] != "1":
        return None

    if weekday == _SUNDAY:
        return course_schedule.sun_end_time
    elif weekday == _MONDAY:
        return course_schedule.mon_end_time
    elif weekday == _TUESDAY:
        return course_schedule.tue_end_time
    elif weekday == _WEDNESDAY:
        return course_schedule.wed_end_time
    elif weekday == _THURSDAY:
        return course_schedule.thu_end_time
    elif weekday == _FRIDAY:
        return course_schedule.fri_end_time
    elif weekday == _SATURDAY:
        return course_schedule.sat_end_time


def _get_comments(course):
    title = course.title
    if course.website:
        title = f"<a href=\"{course.website}\">{title}</a>"

    if not course.is_online and course.room:
        return f"{title} in {course.room}"
    elif course.website:
        return title
    else:
        return ""


def _get_cache_prefix(course):
    return f"users:{course.course_group.user_id}:courses:{course.pk}:coursescheduleevents:"


def _apply_event_filters(event, _from, to, search):
    if _from and to and not (
            (_from <= event.start <= to or _from <= event.end <= to) or
            # Also include results where start/end dates are wider than the window
            (event.start <= _from and event.end >= to)):
        return False

    if search and not (search in event.title.lower() or
                       (event.comments and search in event.comments.lower())):
        return False

    return True


def _get_events_from_cache(course, cache_prefix, cached_value, _from=None, to=None, search=None):
    events = []
    invalid_data = False

    try:
        for event in json.loads(cached_value):
            event = Event(id=event['id'],
                          title=event['title'],
                          all_day=event['all_day'],
                          show_end_time=event['show_end_time'],
                          start=parser.parse(event['start']),
                          end=parser.parse(event['end']),
                          url=event['url'],
                          owner_id=event['owner_id'],
                          user_id=event['user'],
                          calendar_item_type=event['calendar_item_type'],
                          comments=event['comments'])
            event.color = course.color

            if _apply_event_filters(event, _from, to, search):
                events.append(event)
    except (json.JSONDecodeError, KeyError, TypeError):
        invalid_data = True

    if invalid_data:
        events = []
        cache.delete(cache_prefix)

    return events, not invalid_data


def _create_events_from_course_schedules(course, course_schedules, _from=None, to=None, search=None):
    events = []
    events_filtered = []

    exceptions = get_course_exceptions(course)
    course_user = course.get_user()
    user_tz = ZoneInfo(course_user.settings.time_zone)
    comments = _get_comments(course)

    schedule_list = list(course_schedules.all())

    day = course.start_date
    while day <= course.end_date:
        if day in exceptions:
            day += datetime.timedelta(days=1)
            continue

        for course_schedule in schedule_list:
            if course_schedule.days_of_week[enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]] == "1":
                start_time = _get_start_time_for_weekday(course_schedule,
                                                         enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()])
                end_time = _get_end_time_for_weekday(course_schedule,
                                                     enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()])

                start = datetime.datetime.combine(day, start_time).replace(
                    tzinfo=user_tz).astimezone(datetime.timezone.utc)
                end = datetime.datetime.combine(day, end_time).replace(
                    tzinfo=user_tz).astimezone(datetime.timezone.utc)

                event = Event(id=deterministic_id(course_user.pk, course_schedule.pk, start.isoformat(),
                                                  end.isoformat()),
                              title=course.title,
                              all_day=False,
                              show_end_time=True,
                              start=start,
                              end=end,
                              url=course.website,
                              owner_id=course.pk,
                              user=course_user,
                              calendar_item_type=enums.COURSE,
                              comments=comments)
                event.color = course.color

                events.append(event)

                if _apply_event_filters(event, _from, to, search):
                    events_filtered.append(event)

        day += datetime.timedelta(days=1)

    serializer = EventSerializer(events, many=True)
    events_json = json.dumps(serializer.data)
    if len(events_json.encode('utf-8')) <= settings.FEED_MAX_CACHEABLE_SIZE:
        cache.set(_get_cache_prefix(course), events_json, settings.FEED_CACHE_TTL_SECONDS)
    else:
        logger.warning("Cache size {max_cache_size} exceeded max, External Calendar {id}".format(
            max_cache_size=len(events_json.encode('utf-8')),
            id=course.pk))

        metricutils.increment('task.cache.max-size-exceeded')

    return events_filtered


def clear_cached_course_schedule(course):
    """
    For a given course, clear all cached keys for course schedule events.

    :param course: The course to clear keys for.
    """
    cache_prefix = _get_cache_prefix(course)
    cached_keys = cache.keys(cache_prefix + "*")

    cache.delete_many(cached_keys)


def course_schedules_to_events(course, course_schedules, _from=None, to=None, search=None):
    """
    For the given course schedule model, generate an event for each class time within the course's start/end window.

    :param course: The course with a start/end date range to iterate over.
    :param course_schedules: A list of course schedules to generate the events for.
    :param _from: The earliest date by which to filter results.
    :param to: The last date by which to filter results.
    :param search: The search string to filter by.
    :return: A list of event resources.
    """
    events = []

    cached = False
    cache_prefix = _get_cache_prefix(course)
    cached_value = cache.get(_get_cache_prefix(course))
    if cached_value:
        events, cached = _get_events_from_cache(course, cache_prefix, cached_value, _from, to, search)

    if not cached:
        events = _create_events_from_course_schedules(course, course_schedules, _from, to, search)

    return events


def _group_days_by_time_slot(course_schedule):
    """
    Group a course schedule's active weekdays by shared (start_time, end_time) —
    e.g. a schedule with Mon/Wed/Fri at 9am and Thu at 2pm groups into two slots.

    :param course_schedule: The course schedule to group.
    :return: A dict of (start_time, end_time) -> list of active weekdays (Helium day-of-week indices).
    """
    groups = {}

    for weekday in range(7):
        start_time = _get_start_time_for_weekday(course_schedule, weekday)
        if start_time is None:
            continue

        end_time = _get_end_time_for_weekday(course_schedule, weekday)
        groups.setdefault((start_time, end_time), []).append(weekday)

    return groups


def _find_first_occurrence(start_date, weekdays):
    weekday_set = set(weekdays)

    day = start_date
    for _ in range(7):
        if enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()] in weekday_set:
            return day
        day += datetime.timedelta(days=1)

    return None


@dataclass
class CourseScheduleRecurrenceGroup:
    """
    One recurrence group for a `CourseSchedule` — a unique (days, start_time,
    end_time) combination among its active days. Deliberately excludes fields
    the client already has from `Course` (title, color) or doesn't use here
    (`url`, `comments`, unlike `course_schedules_to_events`'s ICS-feed shape).
    """
    start: datetime.datetime
    end: datetime.datetime
    recurrence_rule: str
    exception_dates: list[datetime.datetime]


def course_schedule_to_recurrence_groups(course, course_schedule):
    """
    For a single course schedule, generate one recurrence group per unique
    time-slot among its active days — e.g. a schedule with Mon/Wed/Fri at 9am
    and Thu at 2pm produces two groups, not one.

    :param course: The course with a start/end date range to iterate over.
    :param course_schedule: The course schedule to generate recurrence groups for.
    :return: A list of `CourseScheduleRecurrenceGroup`, one per unique time-slot.
    """
    groups = []

    exceptions = sorted(get_course_exceptions(course))
    user_tz = ZoneInfo(course.get_user().settings.time_zone)

    for (start_time, end_time), weekdays in _group_days_by_time_slot(course_schedule).items():
        first_occurrence = _find_first_occurrence(course.start_date, weekdays)
        if first_occurrence is None or first_occurrence > course.end_date:
            continue

        start = datetime.datetime.combine(first_occurrence, start_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)
        end = datetime.datetime.combine(first_occurrence, end_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)
        until = datetime.datetime.combine(course.end_date, datetime.time(23, 59, 59), tzinfo=user_tz) \
            .astimezone(datetime.timezone.utc)

        exception_dates = [
            datetime.datetime.combine(exception, start_time).replace(tzinfo=user_tz).astimezone(datetime.timezone.utc)
            for exception in exceptions
        ]

        byday = ','.join(WEEKDAY_TO_ICAL[_HELIUM_TO_PYTHON_WEEKDAY[weekday]] for weekday in weekdays)
        recurrence_rule = f'FREQ=WEEKLY;BYDAY={byday};UNTIL={until.strftime("%Y%m%dT%H%M%SZ")}'

        groups.append(CourseScheduleRecurrenceGroup(
            start=start, end=end, recurrence_rule=recurrence_rule, exception_dates=exception_dates))

    return groups
