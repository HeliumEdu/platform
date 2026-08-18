__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import datetime
import logging
from zoneinfo import ZoneInfo

from dateutil.rrule import rrulestr
from django.db import transaction
from rest_framework.exceptions import ValidationError

from helium.feed.services.icalparseservice import parse_events
from helium.planner.models import Course, CourseGroup
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer

logger = logging.getLogger(__name__)

TARGET_COURSE = 'course'
TARGET_NEW_COURSE = 'new_course'
TARGET_EVENTS = 'events'
TARGET_TYPE_CHOICES = (TARGET_COURSE, TARGET_NEW_COURSE, TARGET_EVENTS)

#: Hard ceiling on instances expanded from a single recurring VEVENT, so an unbounded RRULE
#: (no COUNT/UNTIL) can't run away even within a long term window.
_MAX_RECURRENCE_INSTANCES = 366

_DEFAULT_COURSE_TITLE = 'Imported Schedule'
_UNGRADED = '-1/100'
_DEFAULT_PRIORITY = 50


def import_ics(request, calendar, *, target_type, course_id=None, course_group_id=None,
               default_course_title=None):
    """Import a parsed calendar into Helium against the chosen target.

    :param request: The request performing the import (its user owns the created rows).
    :param calendar: A parsed ``icalendar.Calendar``.
    :param target_type: One of ``course``, ``new_course``, ``events``.
    :param course_id: Existing Course id, required when ``target_type == 'course'``.
    :param course_group_id: Course Group id the new Course is created in, required when
        ``target_type == 'new_course'``.
    :param default_course_title: Fallback title for a created Course (typically the upload
        filename) when the calendar carries no ``X-WR-CALNAME``.
    :return: A ``(courses_count, events_count, homework_count)`` tuple (``courses_count`` is 1
        only when ``new_course`` auto-creates one).
    :raises ValidationError: On an unknown ``target_type`` or a missing/unresolvable target id.
    """
    if target_type not in TARGET_TYPE_CHOICES:
        raise ValidationError(
            {'target_type': f"`target_type` must be one of {', '.join(TARGET_TYPE_CHOICES)}."})

    time_zone = ZoneInfo(request.user.settings.time_zone)

    with transaction.atomic():
        if target_type == TARGET_EVENTS:
            events_count = _import_as_events(request, calendar, time_zone)
            return 0, events_count, 0

        course, course_created = _resolve_target_course(
            request, target_type, course_id, course_group_id, calendar, default_course_title)
        homework_count = _import_as_assignments(request, calendar, course, time_zone)
        return (1 if course_created else 0), 0, homework_count


def _resolve_target_course(request, target_type, course_id, course_group_id, calendar,
                           default_course_title):
    """Return a ``(course, created)`` tuple for the assignments target."""
    if target_type == TARGET_COURSE:
        course = Course.objects.for_user(request.user.pk).filter(pk=course_id).first()
        if course is None:
            raise ValidationError({'course': f"Unresolved `course` reference `{course_id}`."})
        return course, False

    course_group = CourseGroup.objects.for_user(request.user.pk).filter(pk=course_group_id).first()
    if course_group is None:
        raise ValidationError(
            {'course_group': f"Unresolved `course_group` reference `{course_group_id}`."})
    return _create_course_in_group(request, course_group, calendar, default_course_title), True


def _create_course_in_group(request, course_group, calendar, default_course_title):
    """Create a net-new Course in the chosen Group, inheriting the Group's term (a Course requires
    a start/end date the calendar does not carry)."""
    title = _derive_course_title(calendar, default_course_title)
    data = {
        'title': title,
        'credits': 0,
        'start_date': course_group.start_date,
        'end_date': course_group.end_date,
    }
    serializer = CourseSerializer(data=data, context={'request': request})
    if not serializer.is_valid():
        raise ValidationError({'course': serializer.errors})
    return serializer.save(course_group_id=course_group.pk)


def _derive_course_title(calendar, default_course_title):
    for prop in ('X-WR-CALNAME', 'NAME'):
        value = calendar.get(prop)
        if isinstance(value, list):
            value = value[0] if value else None
        if value:
            return str(value)
    return default_course_title or _DEFAULT_COURSE_TITLE


def _import_as_assignments(request, calendar, course, time_zone):
    created = 0
    seen_uids = set()

    for parsed in parse_events(calendar, time_zone):
        if _is_duplicate_uid(parsed, seen_uids):
            continue

        duration = parsed['end'] - parsed['start']
        for start in _assignment_start_times(parsed, course.end_date):
            data = {
                'title': parsed['title'],
                'all_day': parsed['all_day'],
                'show_end_time': parsed['show_end_time'],
                'start': start,
                'end': start + duration,
                'priority': _DEFAULT_PRIORITY,
                'current_grade': _UNGRADED,
                'completed': False,
                'comments': parsed['description'] or '',
                'course': course.pk,
                'category': None,
            }
            serializer = HomeworkSerializer(data=data, context={'request': request})
            if not serializer.is_valid():
                raise ValidationError({'homework': serializer.errors})
            serializer.save(course_id=course.pk)
            created += 1

    logger.info(f"Imported {created} assignments from .ics into course {course.pk}.")

    return created


def _import_as_events(request, calendar, time_zone):
    created = 0
    seen_uids = set()

    for parsed in parse_events(calendar, time_zone):
        if _is_duplicate_uid(parsed, seen_uids):
            continue

        _create_event(request, parsed, parsed['start'], parsed['end'],
                      recurrence_rule=parsed['recurrence_rule'],
                      exception_dates=parsed['exception_dates'])
        created += 1

        # RDATE extras can't ride a single RRULE, so each becomes a standalone Event mirroring
        # the parent's duration (matching the external-calendar service).
        duration = parsed['end'] - parsed['start']
        for extra_start in parsed['extra_starts']:
            _create_event(request, parsed, extra_start, extra_start + duration)
            created += 1

    logger.info(f"Imported {created} events from .ics.")

    return created


def _create_event(request, parsed, start, end, *, recurrence_rule=None, exception_dates=None):
    data = {
        'title': parsed['title'],
        'all_day': parsed['all_day'],
        'show_end_time': parsed['show_end_time'],
        'start': start,
        'end': end,
        'priority': _DEFAULT_PRIORITY,
        'url': parsed['url'],
        'comments': parsed['description'] or '',
        'recurrence_rule': recurrence_rule,
        'exception_dates': exception_dates,
    }
    serializer = EventSerializer(data=data)
    if not serializer.is_valid():
        raise ValidationError({'events': serializer.errors})
    serializer.save(user=request.user)


def _assignment_start_times(parsed, window_end_date):
    """Return the UTC start datetimes an Assignment should be created for.

    Non-recurring VEVENT → its single start. Recurring VEVENT → RRULE occurrences (minus
    EXDATEs), bounded by ``window_end_date`` (the course end) and ``_MAX_RECURRENCE_INSTANCES``,
    since Assignments have no recurrence field. RDATE extras are always appended.
    """
    start = parsed['start']
    starts = []

    if parsed['recurrence_rule']:
        exceptions = _exception_datetimes(parsed['exception_dates'])
        try:
            for occurrence in rrulestr(parsed['recurrence_rule'], dtstart=start):
                if occurrence.date() > window_end_date or len(starts) >= _MAX_RECURRENCE_INSTANCES:
                    break
                if occurrence not in exceptions:
                    starts.append(occurrence)
        except (ValueError, TypeError):
            logger.info('Falling back to a single Assignment for an unexpandable RRULE.')
            starts = [start]
    else:
        starts.append(start)

    starts.extend(parsed['extra_starts'])

    return starts


def _exception_datetimes(exception_dates):
    if not exception_dates:
        return set()
    return {datetime.datetime.fromisoformat(iso) for iso in exception_dates}


def _is_duplicate_uid(parsed, seen_uids):
    uid = parsed['uid']
    if not uid:
        return False
    if uid in seen_uids:
        return True
    seen_uids.add(uid)
    return False
