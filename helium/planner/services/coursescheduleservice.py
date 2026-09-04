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

# Which weekdays a cycle schedule advances on and can hold meetings, as Python weekday ints
# (Mon=0). Mon-Fri by default — deliberately the single source of truth so this stays overridable
# (a Saturday-session school, or a future per-schedule field) rather than a scattered assumption.
# The cycle superset RRULE's BYDAY derives from this same set, so the counting and the emitted
# occurrences can never drift apart.
_SCHOOL_WEEKDAYS = (0, 1, 2, 3, 4)


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


def schedule_meeting_times_for_day(course_schedule, day, exceptions):
    """
    The (start_time, end_time) slots a schedule meets on ``day`` — 0 or 1 tuple. Resolved by:
    cycle-day index for a cycle schedule; weekday for a weekly schedule; and weekday *within a
    matching rotation week* for a week-based ("Week A/B") schedule. This is the single source of
    truth every consumer routes through (recurrence groups, the ICS feed, and reminders), so each
    schedule type resolves consistently everywhere.

    :param exceptions: Course/course-group exception dates — a cycle needs them to count school days.
    """
    # A schedule with its own date window only meets within it; its callers already bound the walk by
    # the course dates, so its own overrides are the only extra constraint here.
    if (course_schedule.start_date and day < course_schedule.start_date) or \
            (course_schedule.end_date and day > course_schedule.end_date):
        return []

    if course_schedule.is_cycle:
        index = resolve_cycle_index(course_schedule, day, exceptions)
        if index is None:
            return []
        for slot in course_schedule.cycle_slots:
            if index in slot['indices']:
                return [(datetime.time.fromisoformat(slot['start_time']),
                         datetime.time.fromisoformat(slot['end_time']))]
        return []

    # A week-based row only meets on weeks matching its offset; otherwise it falls through to the
    # ordinary weekday match (it reuses `days_of_week` and the per-weekday times).
    if course_schedule.is_week_based and resolve_week_index(course_schedule, day) != course_schedule.week_offset:
        return []

    weekday = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]
    if course_schedule.days_of_week[weekday] == "1":
        return [(_get_start_time_for_weekday(course_schedule, weekday),
                 _get_end_time_for_weekday(course_schedule, weekday))]
    return []


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
            for start_time, end_time in schedule_meeting_times_for_day(course_schedule, day, exceptions):
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


_DAYS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')


def move_course_schedule_times(course_schedule, from_time_zone, to_time_zone, on_date):
    """
    Move a schedule's times between timezones, using the offset in effect on `on_date`. A time
    carried past midnight rotates `days_of_week` with it, except on rotating schedules, which
    index that field by cycle position and are left alone.

    :param course_schedule: Mutated in place, left unsaved.
    :return: (fields changed, whether a day rotation was skipped)
    """
    converted = {}
    day_delta = 0
    for index, day in enumerate(_DAYS):
        for suffix in ('start_time', 'end_time'):
            value = getattr(course_schedule, f'{day}_{suffix}')
            source = datetime.datetime.combine(on_date, value, tzinfo=from_time_zone)
            target = source.astimezone(to_time_zone)
            converted[(index, suffix)] = target.time()
            if suffix == 'start_time':
                day_delta = (target.date() - source.date()).days

    rotates = day_delta != 0 and not course_schedule.is_rotating
    skipped_rotation = day_delta != 0 and course_schedule.is_rotating

    updated_fields = []
    for index, day in enumerate(_DAYS):
        source_index = (index - day_delta) % 7 if rotates else index
        for suffix in ('start_time', 'end_time'):
            field = f'{day}_{suffix}'
            setattr(course_schedule, field, converted[(source_index, suffix)])
            updated_fields.append(field)

    if rotates:
        course_schedule.days_of_week = ''.join(
            course_schedule.days_of_week[(index - day_delta) % 7] for index in range(7))
        updated_fields.append('days_of_week')

    return updated_fields, skipped_rotation


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


def _is_school_day(date, exceptions):
    """A cycle only advances on school weekdays that aren't course/course-group exceptions."""
    return date.weekday() in _SCHOOL_WEEKDAYS and date not in exceptions


def resolve_cycle_index(course_schedule, date, exceptions):
    """
    For a cycle (rotating / A-B / block) schedule, return the 1-based cycle-day index
    that ``date`` falls on — counting school days forward from ``anchor_date`` (cycle
    "Day 1"), skipping weekends and exception dates so a holiday pushes the cycle onto
    the next school day. Returns ``None`` for a weekly schedule, a date before the
    anchor, a weekend, or an exception date.

    :param course_schedule: The schedule (its ``cycle_length``/``anchor_date`` drive the count).
    :param date: The calendar date to resolve.
    :param exceptions: A set of course/course-group exception dates (see ``get_course_exceptions``).
    :return: The 1-based cycle-day index, or ``None``.
    """
    if not course_schedule.is_cycle or course_schedule.anchor_date is None:
        return None
    if date < course_schedule.anchor_date or not _is_school_day(date, exceptions):
        return None

    school_days = 0
    day = course_schedule.anchor_date
    while day <= date:
        if _is_school_day(day, exceptions):
            school_days += 1
        day += datetime.timedelta(days=1)

    return (school_days - 1) % course_schedule.cycle_length + 1


# Week-based ("Week A/B") rotations always alternate every other week.
_WEEK_ROTATION_INTERVAL = 2


def resolve_week_index(course_schedule, date):
    """
    For a week-based rotation ("Week A/B"), the 0-based week-of-rotation that ``date`` falls in —
    counted from the Monday of ``anchor_date``'s week, mod 2 (weeks alternate A/B). Weeks are
    calendar-aligned, so holidays do NOT shift the count (the opposite of ``resolve_cycle_index``).
    Returns ``None`` for a non-week-based schedule or a missing anchor.

    :param course_schedule: The schedule (its ``anchor_date`` drives the count).
    :param date: The calendar date to resolve.
    :return: The 0-based week-of-rotation index, or ``None``.
    """
    if not course_schedule.is_week_based or course_schedule.anchor_date is None:
        return None

    anchor_monday = course_schedule.anchor_date - datetime.timedelta(days=course_schedule.anchor_date.weekday())
    weeks_since = (date - anchor_monday).days // 7

    return weeks_since % _WEEK_ROTATION_INTERVAL


def course_schedule_to_recurrence_groups(course, course_schedule):
    """
    For a single course schedule, generate one recurrence group per unique time-slot.
    A weekly schedule groups its active weekdays by shared time; a cycle schedule groups
    its `cycle_slots`, resolving each into the same RRULE + exception-dates shape (see
    `_cycle_recurrence_groups`), so the client renders both identically.

    :param course: The course with a start/end date range to iterate over.
    :param course_schedule: The course schedule to generate recurrence groups for.
    :return: A list of `CourseScheduleRecurrenceGroup`, one per unique time-slot.
    """
    exceptions = get_course_exceptions(course)
    user_tz = ZoneInfo(course.get_user().settings.time_zone)
    window = schedule_window(course, course_schedule)

    if course_schedule.is_cycle:
        return _cycle_recurrence_groups(course_schedule, exceptions, user_tz, window)

    if course_schedule.is_week_based:
        return _week_based_recurrence_groups(course_schedule, exceptions, user_tz, window)

    return _weekly_recurrence_groups(course_schedule, exceptions, user_tz, window)


def schedule_window(course, course_schedule):
    """
    A schedule's effective (start, end): its own date overrides, defaulting to the course's dates and
    clamped to the course window so a schedule can only narrow — never widen — its active range.
    """
    start = max(course_schedule.start_date or course.start_date, course.start_date)
    end = min(course_schedule.end_date or course.end_date, course.end_date)
    return start, end


def _weekly_recurrence_groups(course_schedule, exceptions, user_tz, window):
    groups = []

    window_start, window_end = window
    sorted_exceptions = sorted(exceptions)
    until = datetime.datetime.combine(window_end, datetime.time(23, 59, 59), tzinfo=user_tz) \
        .astimezone(datetime.timezone.utc)

    for (start_time, end_time), weekdays in _group_days_by_time_slot(course_schedule).items():
        first_occurrence = _find_first_occurrence(window_start, weekdays)
        if first_occurrence is None or first_occurrence > window_end:
            continue

        start = datetime.datetime.combine(first_occurrence, start_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)
        end = datetime.datetime.combine(first_occurrence, end_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)

        exception_dates = [
            datetime.datetime.combine(exception, start_time).replace(tzinfo=user_tz).astimezone(datetime.timezone.utc)
            for exception in sorted_exceptions
        ]

        byday = ','.join(WEEKDAY_TO_ICAL[_HELIUM_TO_PYTHON_WEEKDAY[weekday]] for weekday in weekdays)
        recurrence_rule = f'FREQ=WEEKLY;BYDAY={byday};UNTIL={until.strftime("%Y%m%dT%H%M%SZ")}'

        groups.append(CourseScheduleRecurrenceGroup(
            start=start, end=end, recurrence_rule=recurrence_rule, exception_dates=exception_dates))

    return groups


def _cycle_recurrence_groups(course_schedule, exceptions, user_tz, window):
    """
    A cycle schedule can't be a single periodic RRULE (its day-count "skips and shifts"
    around holidays). Since the course window is finite, each `cycle_slots` entry is
    expressed as a **superset weekly RRULE over every school weekday** plus an
    **exclusion list** of every weekday in range that isn't actually an occurrence of
    that slot (which naturally absorbs holidays too). Identical `CourseScheduleRecurrenceGroup`
    shape as the weekly path — the client can't tell them apart.
    """
    groups = []

    window_start, window_end = window
    until = datetime.datetime.combine(window_end, datetime.time(23, 59, 59), tzinfo=user_tz) \
        .astimezone(datetime.timezone.utc)

    # Single walk of the term: every school weekday, mapped to its cycle index (holidays absent → None).
    school_days = 0
    index_by_weekday = {}
    all_weekdays = []
    day = course_schedule.anchor_date or window_start
    while day <= window_end:
        if day.weekday() in _SCHOOL_WEEKDAYS:
            if day >= window_start:
                all_weekdays.append(day)
            if _is_school_day(day, exceptions):
                school_days += 1
                if day >= window_start:
                    index_by_weekday[day] = (school_days - 1) % course_schedule.cycle_length + 1
        day += datetime.timedelta(days=1)

    byday = ','.join(WEEKDAY_TO_ICAL[weekday] for weekday in _SCHOOL_WEEKDAYS)

    for slot in course_schedule.cycle_slots:
        indices = set(slot['indices'])
        start_time = datetime.time.fromisoformat(slot['start_time'])
        end_time = datetime.time.fromisoformat(slot['end_time'])

        occurrences = [day for day in all_weekdays if index_by_weekday.get(day) in indices]
        if not occurrences:
            continue

        first_occurrence = occurrences[0]
        occurrence_set = set(occurrences)

        start = datetime.datetime.combine(first_occurrence, start_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)
        end = datetime.datetime.combine(first_occurrence, end_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)

        exception_dates = [
            datetime.datetime.combine(day, start_time).replace(tzinfo=user_tz).astimezone(datetime.timezone.utc)
            for day in all_weekdays if day >= first_occurrence and day not in occurrence_set
        ]

        recurrence_rule = f'FREQ=WEEKLY;BYDAY={byday};UNTIL={until.strftime("%Y%m%dT%H%M%SZ")}'

        groups.append(CourseScheduleRecurrenceGroup(
            start=start, end=end, recurrence_rule=recurrence_rule, exception_dates=exception_dates))

    return groups


def _find_first_week_occurrence(course_schedule, weekdays, window):
    weekday_set = set(weekdays)
    window_start, window_end = window

    day = window_start
    while day <= window_end:
        if enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()] in weekday_set \
                and resolve_week_index(course_schedule, day) == course_schedule.week_offset:
            return day
        day += datetime.timedelta(days=1)

    return None


def _week_based_recurrence_groups(course_schedule, exceptions, user_tz, window):
    """
    A week-based rotation ("Week A/B") is calendar-week-periodic, so — unlike a day cycle — each
    time-slot is a plain periodic RRULE: `FREQ=WEEKLY;INTERVAL=2` anchored to the first
    occurrence in a `week_offset`-matching week (WKST defaults to Monday, matching the anchor-Monday
    week counting). Holidays are ordinary EXDATEs — no shift. Same `CourseScheduleRecurrenceGroup`
    shape as the weekly path, so the client can't tell them apart.
    """
    groups = []

    window_start, window_end = window
    sorted_exceptions = sorted(exceptions)
    until = datetime.datetime.combine(window_end, datetime.time(23, 59, 59), tzinfo=user_tz) \
        .astimezone(datetime.timezone.utc)

    for (start_time, end_time), weekdays in _group_days_by_time_slot(course_schedule).items():
        first_occurrence = _find_first_week_occurrence(course_schedule, weekdays, window)
        if first_occurrence is None:
            continue

        start = datetime.datetime.combine(first_occurrence, start_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)
        end = datetime.datetime.combine(first_occurrence, end_time).replace(
            tzinfo=user_tz).astimezone(datetime.timezone.utc)

        exception_dates = [
            datetime.datetime.combine(exception, start_time).replace(tzinfo=user_tz).astimezone(datetime.timezone.utc)
            for exception in sorted_exceptions
        ]

        byday = ','.join(WEEKDAY_TO_ICAL[_HELIUM_TO_PYTHON_WEEKDAY[weekday]] for weekday in weekdays)
        recurrence_rule = (f'FREQ=WEEKLY;INTERVAL={_WEEK_ROTATION_INTERVAL};BYDAY={byday};'
                           f'UNTIL={until.strftime("%Y%m%dT%H%M%SZ")}')

        groups.append(CourseScheduleRecurrenceGroup(
            start=start, end=end, recurrence_rule=recurrence_rule, exception_dates=exception_dates))

    return groups
