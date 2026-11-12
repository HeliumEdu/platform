import logging
from zoneinfo import ZoneInfo

from django.db import transaction
from rest_framework.exceptions import ValidationError

from helium.common import enums
from helium.feed.services.icalparseservice import parse_events
from helium.planner.models import Category, Course, CourseGroup, Event, Homework
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.services import noteservice, recurrenceservice
from helium.planner.tasks import recalculate_category_grade
from helium.planner.utils.quillutils import plain_text_to_quill

logger = logging.getLogger(__name__)

TARGET_COURSE = 'course'
TARGET_NEW_COURSE = 'new_course'
TARGET_EVENTS = 'events'
TARGET_TYPE_CHOICES = (TARGET_COURSE, TARGET_NEW_COURSE, TARGET_EVENTS)

_DEFAULT_COURSE_TITLE = 'Imported Schedule'
_DEFAULT_PRIORITY = 50


def import_ics(request, calendar, *, target_type, course_id=None, course_group_id=None,
               default_course_title=None, dry_run=False):
    """
    Import a parsed calendar into Helium against the chosen target.

    :param request: The request performing the import (its user owns the created rows).
    :param calendar: A parsed ``icalendar.Calendar``.
    :param target_type: One of ``course``, ``new_course``, ``events``.
    :param course_id: Existing Course id, required when ``target_type == 'course'``.
    :param course_group_id: Course Group id the new Course is created in, required when
        ``target_type == 'new_course'``.
    :param default_course_title: Fallback title for a created Course (typically the upload
        filename) when the calendar carries no ``X-WR-CALNAME``.
    :param dry_run: Validate the import, then roll it back.
    :return: A ``(courses_count, events_count, homework_count)`` tuple (``courses_count`` is 1 only when
        ``new_course`` auto-creates one).
    :raises ValidationError: On an unknown ``target_type``, a missing/unresolvable target id, or a
        calendar that yields nothing importable.
    """
    if target_type not in TARGET_TYPE_CHOICES:
        raise ValidationError(
            {'target_type': f"`target_type` must be one of {', '.join(TARGET_TYPE_CHOICES)}."})

    time_zone = ZoneInfo(request.user.settings.time_zone)

    with transaction.atomic():
        if target_type == TARGET_EVENTS:
            events_count = _import_as_events(request, calendar, time_zone)
            _require_imported(events_count)
            counts = 0, events_count, 0
        else:
            course, course_created = _resolve_target_course(
                request, target_type, course_id, course_group_id, calendar, default_course_title)
            homework_count = _import_as_assignments(request, calendar, course, time_zone)
            _require_imported(homework_count)
            counts = (1 if course_created else 0), 0, homework_count

        if dry_run:
            transaction.set_rollback(True)

    return counts


def _require_imported(count):
    """
    Raise when nothing landed: a `new_course` target has already created its Course, and
    unwinding the transaction is what keeps an empty one from surviving.
    """
    if count == 0:
        raise ValidationError({'details': 'No events in the calendar file could be imported.'})


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
    """
    Create a net-new Course in the chosen Group, inheriting the Group's term (a Course requires
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
    uncategorized = Category.objects.get_uncategorized(course.pk)
    assignments = []
    descriptions = []
    seen_uids = set()

    for parsed in parse_events(calendar, time_zone):
        if _is_duplicate_uid(parsed, seen_uids):
            continue

        assignments.append(_build_assignment(request, parsed, parsed['start'], parsed['end'], course, uncategorized,
                                             recurrence_rule=parsed['recurrence_rule'],
                                             exception_dates=parsed['exception_dates']))
        descriptions.append(parsed['description'])

        duration = parsed['end'] - parsed['start']
        for extra_start in parsed['extra_starts']:
            assignments.append(_build_assignment(request, parsed, extra_start, extra_start + duration, course,
                                                 uncategorized))
            descriptions.append(parsed['description'])

    _create_with_description_notes(request, Homework, assignments, descriptions, 'homework')
    if assignments:
        recalculate_category_grade.apply(args=(uncategorized.pk,))

    logger.info(f"Imported {len(assignments)} assignments from .ics into course {course.pk}.")

    return len(assignments)


def _build_assignment(request, parsed, start, end, course, category, *, recurrence_rule=None, exception_dates=None):
    data = {
        'title': parsed['title'],
        'all_day': parsed['all_day'],
        'show_end_time': parsed['show_end_time'],
        'start': start,
        'end': end,
        'priority': _DEFAULT_PRIORITY,
        'url': parsed['url'],
        'current_grade': enums.UNGRADED,
        'completed': False,
        'recurrence_rule': recurrence_rule,
        'exception_dates': exception_dates,
    }
    serializer = HomeworkSerializer(data=data, context={'request': request}, partial=True)
    if not serializer.is_valid():
        raise ValidationError({'homework': serializer.errors})
    validated = serializer.validated_data
    if validated.get('recurrence_rule'):
        try:
            validated['recurrence_rule'] = recurrenceservice.bound_to_course(
                validated['recurrence_rule'], start, end, validated['all_day'], course)
        except ValidationError as ex:
            raise ValidationError({'homework': f"\"{parsed['title']}\": {ex.detail['recurrence_rule']}"})
    return Homework(**validated, course=course, category=category)


def _import_as_events(request, calendar, time_zone):
    events = []
    descriptions = []
    seen_uids = set()

    for parsed in parse_events(calendar, time_zone):
        if _is_duplicate_uid(parsed, seen_uids):
            continue

        events.append(_build_event(request, parsed, parsed['start'], parsed['end'],
                                   recurrence_rule=parsed['recurrence_rule'],
                                   exception_dates=parsed['exception_dates']))
        descriptions.append(parsed['description'])

        # RDATE extras can't ride a single RRULE, so each becomes a standalone Event mirroring
        # the parent's duration (matching the external-calendar service).
        duration = parsed['end'] - parsed['start']
        for extra_start in parsed['extra_starts']:
            events.append(_build_event(request, parsed, extra_start, extra_start + duration))
            descriptions.append(parsed['description'])

    _create_with_description_notes(request, Event, events, descriptions, 'events')

    logger.info(f"Imported {len(events)} events from .ics.")

    return len(events)


def _build_event(request, parsed, start, end, *, recurrence_rule=None, exception_dates=None):
    data = {
        'title': parsed['title'],
        'all_day': parsed['all_day'],
        'show_end_time': parsed['show_end_time'],
        'start': start,
        'end': end,
        'priority': _DEFAULT_PRIORITY,
        'url': parsed['url'],
        'recurrence_rule': recurrence_rule,
        'exception_dates': exception_dates,
    }
    serializer = EventSerializer(data=data)
    if not serializer.is_valid():
        raise ValidationError({'events': serializer.errors})
    return Event(**serializer.validated_data, user=request.user)


def _create_with_description_notes(request, model, instances, descriptions, section):
    """
    Create the imported rows, giving each one whose calendar entry carries a DESCRIPTION a linked
    Note holding that text. Rows without one are bulk created; a row with one is saved on its own,
    since linking the Note needs a primary key that a MySQL bulk create does not return.
    """
    note_contents = [plain_text_to_quill(description) for description in descriptions]

    model.objects.bulk_create([instance for instance, content in zip(instances, note_contents) if not content])

    for instance, content in zip(instances, note_contents):
        if not content:
            continue
        instance.save()
        try:
            noteservice.create_linked_note(content, request.user, instance, context={'request': request})
        except ValidationError as e:
            raise ValidationError({section: e.detail})


def _is_duplicate_uid(parsed, seen_uids):
    uid = parsed['uid']
    if not uid:
        return False
    if uid in seen_uids:
        return True
    seen_uids.add(uid)
    return False
