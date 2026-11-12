import datetime
import json
import logging
import os
from contextlib import contextmanager
from decimal import Decimal
from typing import Dict, NamedTuple
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from helium.common import enums
from helium.common.utils import datetimeutils, gradeutils, metricutils, taskutils
from helium.common.utils.datetimeutils import local_midnight_as_utc
from helium.common.utils.validators import shift_recurrence_rule_for_user
from helium.common.utils.course_exception_helpers import get_course_exceptions
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, Course, CourseSchedule, Homework, Event, Category, Reminder, \
    ResourceGroup, Resource
from helium.importexport.services import examplescheduleguardservice, legacyimportparity
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.resourcegroupserializer import ResourceGroupSerializer
from helium.planner.serializers.resourceserializer import ResourceSerializer
from helium.planner.serializers.noteserializer import NoteSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.services import coursescheduleservice
from helium.planner.services import gradingservice
from helium.planner.services import reminderservice
from helium.planner.tasks import adjust_reminder_times, recalculate_category_grades_for_course

logger = logging.getLogger(__name__)

_SECTIONS_WITH_IDS = (
    'external_calendars', 'course_groups', 'courses', 'course_schedules', 'categories',
    'resource_groups', 'resources', 'events', 'homework', 'reminders', 'notes',
)

_SUPPRESSED_SENDERS = frozenset({Course, CourseSchedule, Category, Homework, Event})


def _row_validation_error(section, row_id, errors):
    """
    Flatten a row's serializer errors into messages naming the section and `id` they came from,
    so a bare field name can't be read as belonging to the wrong entity.
    """
    messages = []
    for field, field_errors in errors.items():
        for error in (field_errors if isinstance(field_errors, (list, tuple)) else [field_errors]):
            messages.append(f'{section} id {row_id}, {field}: {error}')

    return ValidationError({section: messages})


class _SectionErrors:
    """
    Collect every row error in a section, so one 400 lists them all, each naming the row it came from. Later sections
    reference this one's ids, so the import stops at the end of the first section with errors.
    """

    def __init__(self, section):
        self.section = section
        self.messages = []

    @contextmanager
    def row(self, row_id):
        try:
            yield
        except ValidationError as error:
            detail = dict(error.detail) if isinstance(error.detail, dict) else {'non_field_errors': error.detail}
            own = detail.pop(self.section, [])
            self.messages.extend(str(message) for message in (own if isinstance(own, list) else [own]))
            if detail:
                self.messages.extend(str(message) for message in
                                     _row_validation_error(self.section, row_id, detail).detail[self.section])

    def raise_if_any(self):
        if self.messages:
            raise ValidationError({self.section: self.messages})


def _coerce_id(value, section, key='id'):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({section: f"Invalid `{key}` value: {value!r} is not a valid id."})


def _validate_section_ids(data):
    """
    Pre-pass over the payload to verify all row ids are integer or integer-coercible strings, and
    that ids within a section are unique. Surfaces malformed hand-rolled files as a clean 400.
    """
    for section in _SECTIONS_WITH_IDS:
        rows = data.get(section, []) or []
        if not isinstance(rows, list):
            raise ValidationError({section: f"Section `{section}` must be a list."})

        seen = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValidationError({section: f"Row {index} in `{section}` must be an object."})

            if 'id' not in row:
                raise ValidationError({section: f"Row {index} in `{section}` is missing required key `id`."})

            coerced = _coerce_id(row['id'], section)
            if coerced in seen:
                raise ValidationError({section: f"Duplicate id `{coerced}` in `{section}`."})
            seen.add(coerced)
            row['id'] = coerced


def _resolve_parent(remap, raw_id, section, parent_key):
    """
    Resolve a parent FK id via the remap dict. Raises ValidationError if the id is missing or
    doesn't resolve — surfaces hand-rolled broken references as 400 rather than letting them
    crash deeper in the stack as IntegrityError → 500.
    """
    if raw_id is None:
        raise ValidationError(
            {section: f"Missing required parent reference `{parent_key}` in section `{section}`."})

    coerced = _coerce_id(raw_id, section, key=parent_key)
    resolved = remap.get(coerced)
    if resolved is None:
        raise ValidationError(
            {section: f"Unresolved `{parent_key}` reference `{coerced}` in section `{section}`."})
    return resolved


def _import_external_calendars(external_calendars, user, example_schedule):
    errors = _SectionErrors('external_calendars')
    for external_calendar in external_calendars:
        with errors.row(external_calendar['id']):
            serializer = ExternalCalendarSerializer(data=external_calendar)

            if serializer.is_valid():
                serializer.save(user=user, example_schedule=example_schedule)
            else:
                raise _row_validation_error('external_calendars', external_calendar['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(external_calendars)} external calendars.")

    return len(external_calendars)


def _import_course_groups(course_groups, user, example_schedule):
    course_group_remap = {}

    errors = _SectionErrors('course_groups')
    for course_group in course_groups:
        with errors.row(course_group['id']):
            serializer = CourseGroupSerializer(data=course_group)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=example_schedule)
                course_group_remap[course_group['id']] = instance.pk
            else:
                raise _row_validation_error('course_groups', course_group['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(course_groups)} course groups.")

    return course_group_remap


def _import_courses(courses, course_group_remap, existing_course_group_id=None):
    course_remap = {}

    errors = _SectionErrors('courses')
    for course in courses:
        with errors.row(course['id']):
            course.pop('template', None)

            course_group_id = existing_course_group_id or _resolve_parent(
                course_group_remap, course.get('course_group'), 'courses', 'course_group')
            course['course_group'] = course_group_id

            serializer = CourseSerializer(data=course)

            if serializer.is_valid():
                instance = serializer.save(course_group_id=course_group_id)
                course_remap[course['id']] = instance.pk
            else:
                raise _row_validation_error('courses', course['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(courses)} courses.")

    return course_remap


def _import_course_schedules(course_schedules, course_remap):
    errors = _SectionErrors('course_schedules')
    for course_schedule in course_schedules:
        with errors.row(course_schedule['id']):
            course_id = _resolve_parent(
                course_remap, course_schedule.get('course'), 'course_schedules', 'course')
            course_schedule['course'] = course_id

            serializer = CourseScheduleSerializer(data=course_schedule)

            if serializer.is_valid():
                serializer.save(course_id=course_id)
            else:
                raise _row_validation_error('course_schedules', course_schedule['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(course_schedules)} course schedules.")

    return len(course_schedules)


def _import_categories(categories, request, course_remap):
    category_remap = {}

    errors = _SectionErrors('categories')
    for category in categories:
        with errors.row(category['id']):
            course_id = _resolve_parent(course_remap, category.get('course'), 'categories', 'course')
            request.parser_context['kwargs']['course'] = course_id

            serializer = CategorySerializer(data=category, context={'request': request})

            if serializer.is_valid():
                instance = serializer.save(course_id=course_id)
                category_remap[category['id']] = instance.pk
            else:
                raise _row_validation_error('categories', category['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(categories)} categories.")

    return category_remap


def _ensure_courses_have_categories(course_remap):
    for course_id in course_remap.values():
        if not Category.objects.filter(course_id=course_id).exists():
            Category.objects.get_uncategorized(course_id)


def _import_resource_groups(resource_groups, user, example_schedule):
    resource_group_remap = {}

    errors = _SectionErrors('resource_groups')
    for resource_group in resource_groups:
        with errors.row(resource_group['id']):
            serializer = ResourceGroupSerializer(data=resource_group)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=example_schedule)
                resource_group_remap[resource_group['id']] = instance.pk
            else:
                raise _row_validation_error('resource_groups', resource_group['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(resource_groups)} resource groups.")

    return resource_group_remap


def _import_resources(resources, resource_group_remap, course_remap, user, example_schedule):
    resource_remap = {}

    errors = _SectionErrors('resources')
    for resource in resources:
        with errors.row(resource['id']):
            resource_group_id = _resolve_parent(
                resource_group_remap, resource.get('resource_group'), 'resources', 'resource_group')
            resource['resource_group'] = resource_group_id

            courses = resource.get('courses') or []
            if not isinstance(courses, list):
                raise ValidationError({'resources': "Field `courses` must be a list."})
            for i, course in enumerate(courses):
                courses[i] = _resolve_parent(course_remap, course, 'resources', 'courses')
            resource['courses'] = courses

            serializer = ResourceSerializer(data=resource)

            if serializer.is_valid():
                instance = serializer.save(resource_group_id=resource_group_id)
                resource_remap[resource['id']] = instance.pk
            else:
                raise _row_validation_error('resources', resource['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(resources)} resources.")

    return resource_remap


def _import_events(events, user, example_schedule):
    event_remap = {}

    errors = _SectionErrors('events')
    for event in events:
        with errors.row(event['id']):
            serializer = EventSerializer(data=event)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=example_schedule)
                event_remap[event['id']] = instance.pk
            else:
                raise _row_validation_error('events', event['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(events)} events.")

    return event_remap


def _import_homework(homework, course_remap, category_remap, resource_remap, user, example_schedule):
    homework_remap = {}
    course_by_category = dict(Category.objects.filter(pk__in=category_remap.values()).values_list('pk', 'course_id'))

    errors = _SectionErrors('homework')
    for h in homework:
        with errors.row(h['id']):
            course_id = _resolve_parent(course_remap, h.get('course'), 'homework', 'course')
            h['course'] = course_id

            if h.get('category'):
                h['category'] = _resolve_parent(category_remap, h.get('category'), 'homework', 'category')
                if course_by_category.get(h['category']) != course_id:
                    logger.info(f"Homework {h.get('id')} imported into Uncategorized; its category belongs to another course")
                    h['category'] = None
            else:
                h['category'] = None

            resources = h.get('resources') or []
            if not isinstance(resources, list):
                raise ValidationError({'homework': "Field `resources` must be a list."})
            for i, resource in enumerate(resources):
                resources[i] = _resolve_parent(resource_remap, resource, 'homework', 'resources')
            h['resources'] = resources

            serializer = HomeworkSerializer(data=h)

            if serializer.is_valid():
                instance = serializer.save(course_id=course_id)
                homework_remap[h['id']] = instance.pk

                # completed_at is read-only (inferred by Homework.save() the first time completed flips true),
                # so the serializer ignores it. Restore the original value from a user's own export rather
                # than letting save() re-stamp it to import time. Seed imports keep the fresh stamp.
                completed_at = parse_datetime(h['completed_at']) if h.get('completed_at') else None
                if completed_at and not example_schedule:
                    Homework.objects.filter(pk=instance.pk).update(completed_at=completed_at)
            else:
                raise _row_validation_error('homework', h['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(homework)} homework.")

    return homework_remap


def _import_reminders(reminders, user, event_remap, homework_remap, course_remap):
    seen_active_series = set()
    created = 0
    errors = _SectionErrors('reminders')
    for reminder in reminders:
        with errors.row(reminder.get('id')):
            reminder['homework'] = _resolve_parent(
                homework_remap, reminder.get('homework'), 'reminders', 'homework') \
                if reminder.get('homework') else None
            reminder['event'] = _resolve_parent(
                event_remap, reminder.get('event'), 'reminders', 'event') \
                if reminder.get('event') else None
            reminder['course'] = _resolve_parent(
                course_remap, reminder.get('course'), 'reminders', 'course') \
                if reminder.get('course') else None

            # A course series holds one active reminder; `message` does not distinguish a series.
            if reminder.get('course') and not reminder.get('sent') and not reminder.get('dismissed'):
                series_key = (reminder.get('course'), reminder.get('type'),
                              reminder.get('offset'), reminder.get('offset_type'))
                if series_key in seen_active_series:
                    continue
                seen_active_series.add(series_key)

            serializer = ReminderSerializer(data=reminder)

            if serializer.is_valid():
                serializer.save(user=user)
                created += 1
            else:
                raise _row_validation_error('reminders', reminder.get('id'), serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {created} reminders.")

    return created


def _import_notes(notes, user, homework_remap, event_remap, resource_remap, course_remap, example_schedule):
    """
    Import notes via NoteSerializer, including those linked to entities. Handles both standalone
    notes and notes linked to homework/events/resources/courses. Entity ids are remapped to
    their newly-created values before serializer validation, so an unresolved id surfaces as a
    clean 400 rather than silently dropping the link.
    """
    notes_count = 0

    errors = _SectionErrors('notes')
    for note_data in notes:
        with errors.row(note_data['id']):
            if not isinstance(note_data, dict):
                raise ValidationError({'notes': "Each note must be an object."})

            payload = {
                'title': note_data.get('title', ''),
                'content': note_data.get('content') or {},
                'homework': [
                    _resolve_parent(homework_remap, raw_id, 'notes', 'homework')
                    for raw_id in (note_data.get('homework') or [])
                ],
                'events': [
                    _resolve_parent(event_remap, raw_id, 'notes', 'events')
                    for raw_id in (note_data.get('events') or [])
                ],
                'resources': [
                    _resolve_parent(resource_remap, raw_id, 'notes', 'resources')
                    for raw_id in (note_data.get('resources') or [])
                ],
                'courses': [
                    _resolve_parent(course_remap, raw_id, 'notes', 'courses')
                    for raw_id in (note_data.get('courses') or [])
                ],
            }

            serializer = NoteSerializer(data=payload)
            if not serializer.is_valid():
                raise _row_validation_error('notes', note_data['id'], serializer.errors)
            serializer.save(user=user, example_schedule=example_schedule)
            notes_count += 1
    errors.raise_if_any()

    logger.info(f"Imported {notes_count} notes.")

    return notes_count


@contextmanager
def suppress_post_save_signals():
    """
    Skip the per-row grade and reminder recalculations an import makes redundant.

    Swaps the process-wide receiver list, so every thread sees it. Safe only where the caller owns
    the process, as a prefork Celery worker does; never use it to serve a request.
    """
    sender_ids = {id(s) for s in _SUPPRESSED_SENDERS}
    original_receivers = post_save.receivers
    post_save.receivers = [
        item for item in original_receivers
        if not (isinstance(item[0], tuple) and len(item[0]) >= 2 and item[0][1] in sender_ids)
    ]
    post_save.sender_receivers_cache.clear()
    try:
        yield
    finally:
        post_save.receivers = original_receivers
        post_save.sender_receivers_cache.clear()


class _ImportedExampleSchedule(NamedTuple):
    """
    The remaps one seed import produced. A user can hold several example schedules, all
    flagged `example_schedule`, so the rebase scopes to these rather than to that flag.
    """

    course_group_remap: Dict[int, int]
    course_remap: Dict[int, int]
    category_remap: Dict[int, int]
    resource_group_remap: Dict[int, int]
    resource_remap: Dict[int, int]
    event_remap: Dict[int, int]
    homework_remap: Dict[int, int]

    def ids(self):
        """
        The ids the import assigned, by section (as the API names them), then by the id each row had in the file.
        """
        return {
            'course_groups': self.course_group_remap,
            'courses': self.course_remap,
            'categories': self.category_remap,
            'resource_groups': self.resource_group_remap,
            'resources': self.resource_remap,
            'events': self.event_remap,
            'homework': self.homework_remap,
        }


@transaction.atomic
def _bulk_import_example_schedule(data, user):
    course_group_remap = {}
    course_remap = {}
    category_remap = {}
    resource_group_remap = {}
    resource_remap = {}
    event_remap = {}
    homework_remap = {}

    # --- CourseGroup ---
    for cg in data.get('course_groups', []):
        instance = CourseGroup.objects.create(
            title=cg['title'],
            start_date=cg['start_date'],
            end_date=cg['end_date'],
            shown_on_calendar=cg.get('shown_on_calendar', True),
            overall_grade=Decimal(cg.get('overall_grade', '-1')),
            trend=cg.get('trend'),
            grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_0),
            grade_scale_template=enums.GRADE_SCALE_4_0,
            exceptions=cg.get('exceptions', ''),
            example_schedule=True,
            user=user,
        )
        course_group_remap[cg['id']] = instance.pk

    # --- Course ---
    for c in data.get('courses', []):
        instance = Course.objects.create(
            title=c['title'],
            room=c.get('room', ''),
            credits=Decimal(c.get('credits', '0')),
            color=c.get('color', '#000000'),
            website=c.get('website') or None,
            is_online=c.get('is_online', False),
            current_grade=Decimal(c.get('current_grade', '-1')),
            trend=c.get('trend'),
            teacher_name=c.get('teacher_name', ''),
            teacher_email=c.get('teacher_email') or '',
            start_date=c['start_date'],
            end_date=c['end_date'],
            exceptions=c.get('exceptions', ''),
            course_group_id=course_group_remap[c['course_group']],
        )
        course_remap[c['id']] = instance.pk

    # --- CourseSchedule ---
    schedule_objects = []
    for cs in data.get('course_schedules', []):
        schedule_objects.append(CourseSchedule(
            days_of_week=cs['days_of_week'],
            sun_start_time=cs['sun_start_time'],
            sun_end_time=cs['sun_end_time'],
            mon_start_time=cs['mon_start_time'],
            mon_end_time=cs['mon_end_time'],
            tue_start_time=cs['tue_start_time'],
            tue_end_time=cs['tue_end_time'],
            wed_start_time=cs['wed_start_time'],
            wed_end_time=cs['wed_end_time'],
            thu_start_time=cs['thu_start_time'],
            thu_end_time=cs['thu_end_time'],
            fri_start_time=cs['fri_start_time'],
            fri_end_time=cs['fri_end_time'],
            sat_start_time=cs['sat_start_time'],
            sat_end_time=cs['sat_end_time'],
            course_id=course_remap[cs['course']],
        ))
    CourseSchedule.objects.bulk_create(schedule_objects)

    # --- Category ---
    categories = data.get('categories', [])
    Category.objects.bulk_create([
        Category(
            title=cat['title'],
            weight=Decimal(cat.get('weight', '0')),
            color=cat.get('color', '#000000'),
            average_grade=Decimal(cat.get('average_grade', '-1')),
            grade_by_weight=Decimal(cat.get('grade_by_weight', '0')),
            trend=cat.get('trend'),
            course_id=course_remap[cat['course']],
        )
        for cat in categories
    ])
    category_pks_by_key = {
        (course_id, title): pk
        for pk, course_id, title in Category.objects.filter(
            course_id__in=course_remap.values()).values_list('pk', 'course_id', 'title')
    }
    for cat in categories:
        category_remap[cat['id']] = category_pks_by_key[(course_remap[cat['course']], cat['title'])]

    # --- ResourceGroup ---
    for rg in data.get('resource_groups', []):
        instance = ResourceGroup.objects.create(
            title=rg['title'],
            shown_on_calendar=rg.get('shown_on_calendar', True),
            example_schedule=True,
            user=user,
        )
        resource_group_remap[rg['id']] = instance.pk

    # --- Resource (with M2M courses) ---
    ResourceCourseThrough = Resource.courses.through
    m2m_rows = []
    for m in data.get('resources', []):
        instance = Resource.objects.create(
            title=m['title'],
            status=m.get('status', enums.OWNED),
            condition=m.get('condition', enums.BRAND_NEW),
            website=m.get('website') or None,
            price=m.get('price', ''),
            resource_group_id=resource_group_remap[m['resource_group']],
        )
        resource_remap[m['id']] = instance.pk
        for course_id in [course_remap[c] for c in m.get('courses', [])]:
            m2m_rows.append(ResourceCourseThrough(resource_id=instance.pk, course_id=course_id))

    if m2m_rows:
        ResourceCourseThrough.objects.bulk_create(m2m_rows)

    # --- ExternalCalendar ---
    for ec in data.get('external_calendars', []):
        ExternalCalendar.objects.create(
            title=ec['title'],
            url=ec['url'],
            color=ec.get('color', '#000000'),
            shown_on_calendar=ec.get('shown_on_calendar', True),
            example_schedule=True,
            user=user,
        )

    # --- Event ---
    for e in data.get('events', []):
        instance = Event.objects.create(
            title=e['title'],
            all_day=e.get('all_day', False),
            show_end_time=e.get('show_end_time', False),
            start=e['start'],
            end=e['end'],
            priority=e.get('priority', 50),
            url=e.get('url') or None,
            owner_id=e.get('owner_id') or None,
            recurrence_rule=e.get('recurrence_rule'),
            exception_dates=e.get('exception_dates'),
            example_schedule=True,
            user=user,
        )
        event_remap[e['id']] = instance.pk

    # --- Homework (individual save for auto-category + completed_at) ---
    hw_resource_m2m = []
    for h in data.get('homework', []):
        instance = Homework(
            title=h['title'],
            all_day=h.get('all_day', False),
            show_end_time=h.get('show_end_time', False),
            start=h['start'],
            end=h['end'],
            priority=h.get('priority', 50),
            url=h.get('url') or None,
            current_grade=h.get('current_grade', ''),
            completed=h.get('completed', False),
            category_id=category_remap.get(h['category']) if h.get('category') else None,
            course_id=course_remap[h['course']],
            recurrence_rule=h.get('recurrence_rule'),
            exception_dates=h.get('exception_dates'),
        )
        instance.save()
        homework_remap[h['id']] = instance.pk
        hw_resource_m2m.append((instance.pk, [resource_remap[m] for m in h.get('resources', [])]))

    HomeworkResourceThrough = Homework.resources.through
    hw_m2m_rows = []
    for hw_pk, resource_ids in hw_resource_m2m:
        for resource_id in resource_ids:
            hw_m2m_rows.append(HomeworkResourceThrough(homework_id=hw_pk, resource_id=resource_id))
    if hw_m2m_rows:
        HomeworkResourceThrough.objects.bulk_create(hw_m2m_rows)

    # --- Reminder (individual save for start_of_range computation) ---
    for r in data.get('reminders', []):
        instance = Reminder(
            message=r.get('message', ''),
            offset=r.get('offset', 30),
            offset_type=r.get('offset_type', enums.MINUTES),
            type=r.get('type', enums.PUSH),
            sent=r.get('sent', False),
            dismissed=r.get('dismissed', False),
            homework_id=homework_remap[r['homework']] if r.get('homework') else None,
            event_id=event_remap[r['event']] if r.get('event') else None,
            course_id=course_remap[r['course']] if r.get('course') else None,
            user=user,
        )
        instance.save()

    notes = data.get('notes', [])
    if notes:
        _import_notes(notes, user, homework_remap, event_remap, resource_remap, course_remap, example_schedule=True)

    metricutils.increment("user.import.schedule")

    logger.info(
        f"Bulk imported example schedule: {len(course_group_remap)} course groups, "
        f"{len(course_remap)} courses, {len(data.get('course_schedules', []))} schedules, "
        f"{len(category_remap)} categories, {len(resource_group_remap)} resource groups, "
        f"{len(resource_remap)} resources, {len(data.get('external_calendars', []))} external calendars, "
        f"{len(event_remap)} events, "
        f"{len(homework_remap)} homework, {len(data.get('reminders', []))} reminders, "
        f"{len(data.get('notes', []))} notes"
    )

    return _ImportedExampleSchedule(
        course_group_remap=course_group_remap,
        course_remap=course_remap,
        category_remap=category_remap,
        resource_group_remap=resource_group_remap,
        resource_remap=resource_remap,
        event_remap=event_remap,
        homework_remap=homework_remap,
    )


@transaction.atomic
def import_user(request, data, example_schedule=False, dry_run=False, course_group_id=None):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param data: The data that will be imported for the user.
    :param dry_run: Validate the import, then roll it back.
    :param course_group_id: An existing Course Group of the user's to import every Course into, in place of the
                            file's Course Groups (which are not imported).
    :return: The counts imported per section, and the ids assigned (by section, then by the id in the file).
    """
    counts, imported = _import_user(request, data, example_schedule, course_group_id)

    if dry_run:
        transaction.set_rollback(True)

    return counts, imported.ids()


def _verify_course_group_is_users(course_group_id, user):
    if not CourseGroup.objects.for_user(user.pk).filter(pk=course_group_id).exists():
        raise ValidationError({'course_group': f"Unresolved `course_group` reference `{course_group_id}`."})


def _import_user(request, data, example_schedule=False, course_group_id=None):
    if not isinstance(data, dict):
        raise ValidationError("Import payload must be a JSON object.")

    legacyimportparity.upgrade_legacy_import(data)

    if course_group_id is not None:
        _verify_course_group_is_users(course_group_id, request.user)
        data['course_groups'] = []

    _validate_section_ids(data)

    external_calendars = data.get('external_calendars', [])
    external_calendar_count = _import_external_calendars(external_calendars, request.user,
                                                         example_schedule) if external_calendars else 0

    course_groups = data.get('course_groups', [])
    course_group_remap = _import_course_groups(course_groups, request.user, example_schedule) if course_groups else {}

    courses = data.get('courses', [])
    course_remap = _import_courses(courses, course_group_remap, course_group_id) if courses else {}

    course_schedules = data.get('course_schedules', [])
    course_schedules_count = _import_course_schedules(course_schedules, course_remap) if course_schedules else 0

    categories = data.get('categories', [])
    category_remap = _import_categories(categories, request, course_remap) if categories else {}

    _ensure_courses_have_categories(course_remap)

    resource_groups = data.get('resource_groups', [])
    resource_group_remap = _import_resource_groups(resource_groups, request.user,
                                                   example_schedule) if resource_groups else {}

    resources = data.get('resources', [])
    resource_remap = _import_resources(resources, resource_group_remap, course_remap, request.user,
                                       example_schedule) if resources else {}

    events = data.get('events', [])
    event_remap = _import_events(events, request.user, example_schedule) if events else {}

    homework = data.get('homework', [])
    homework_remap = _import_homework(homework, course_remap, category_remap, resource_remap, request.user,
                                      example_schedule) if homework else {}

    reminders = data.get('reminders', [])
    reminders_count = _import_reminders(reminders, request.user, event_remap, homework_remap, course_remap) if reminders else 0

    notes = data.get('notes', [])
    notes_count = _import_notes(notes, request.user, homework_remap, event_remap, resource_remap, course_remap,
                                example_schedule) if notes else 0

    for course_id in set(course_remap.values()):
        transaction.on_commit(lambda course_id=course_id: taskutils.safe_apply_async(
            recalculate_category_grades_for_course, args=(course_id,), priority=settings.CELERY_PRIORITY_LOW))

    transaction.on_commit(lambda: metricutils.increment("user.import.schedule"))

    counts = (external_calendar_count, len(course_group_remap), len(course_remap), course_schedules_count,
              len(category_remap), len(resource_group_remap), len(resource_remap), len(event_remap),
              len(homework_remap), reminders_count, notes_count)

    return counts, _ImportedExampleSchedule(
        course_group_remap=course_group_remap,
        course_remap=course_remap,
        category_remap=category_remap,
        resource_group_remap=resource_group_remap,
        resource_remap=resource_remap,
        event_remap=event_remap,
        homework_remap=homework_remap,
    )


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
    day = min(today, course.end_date)

    while day >= course.start_date:
        if day in exceptions:
            day -= datetime.timedelta(days=1)
            continue

        # Multiple schedules can meet the same day (lecture + lab, or a cycle-day slot) — take the latest.
        candidates = []
        for course_schedule in course_schedules:
            for start_time, _end_time in coursescheduleservice.schedule_meeting_times_for_day(
                    course_schedule, day, exceptions):
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


def _adjust_schedule_relative_to(user, adjust_month, imported, source_tz=None):
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


def import_example_schedule(user):
    with open(os.path.join(os.path.dirname(__file__), '..', 'resources', 'example_schedule.json'), 'rb') as f:
        json_str = f.read().decode('utf-8')

    try:
        data = json.loads(json_str)

        # Fixture-internal, never read by the nominal import path.
        source_time_zone = data.get('time_zone')
        if source_time_zone:
            source_tz = ZoneInfo(source_time_zone)
        else:
            source_tz = None
            logger.warning('Example schedule declares no time_zone, leaving class times as authored')

        with transaction.atomic():
            examplescheduleguardservice.promote_modified(user.pk)

            imported = _bulk_import_example_schedule(data, user)

            _adjust_schedule_relative_to(user, -1, imported, source_tz)

            for category_id in Category.objects.for_user(user.pk).values_list('pk', flat=True):
                gradingservice.recalculate_category_grade(category_id)

            course_group_ids = set()
            for course in (Course.objects.for_user(user.pk)
                    .filter(course_group__example_schedule=True)
                    .select_related('course_group')):
                gradingservice.recalculate_course_grade(course.pk, course.course_group.grade_scale)
                course_group_ids.add(course.course_group_id)

            for course_group_id in course_group_ids:
                gradingservice.recalculate_course_group_grade(course_group_id)

            user.example_schedule_imported_at = timezone.now()
            get_user_model().objects.filter(pk=user.pk).update(
                example_schedule_imported_at=user.example_schedule_imported_at)
    except ValueError:
        raise ValidationError({
            'details': 'Invalid JSON.'
        })
