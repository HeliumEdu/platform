__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import logging
import os
from contextlib import contextmanager
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.http import HttpRequest
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from helium.common import enums
from helium.common.utils import metricutils, taskutils
from helium.common.utils.commonutils import local_midnight_as_utc
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, Course, CourseSchedule, Homework, Event, Category, Reminder, \
    MaterialGroup, Material
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.serializers.noteserializer import NoteSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.services import coursescheduleservice
from helium.planner.services import gradingservice
from helium.planner.services import reminderservice
from helium.planner.tasks import adjust_reminder_times, recalculate_category_grades_for_course
from helium.planner.utils.quillutils import html_to_quill
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiListView

logger = logging.getLogger(__name__)


def _extract_legacy_notes(data, legacy_field='comments'):
    """
    Extract and convert legacy HTML notes field to Quill JSON format.

    Reads the legacy field from data (preserving it) and returns the converted Quill JSON content.
    Returns None if no legacy content or conversion fails.

    :param data: The entity data dict (legacy field is preserved)
    :param legacy_field: The name of the legacy field ('comments' or 'details')
    :return: Quill JSON content dict or None
    """
    legacy_content = data.get(legacy_field, None)

    if legacy_content:
        return html_to_quill(legacy_content)

    return None


_SECTIONS_WITH_IDS = (
    'external_calendars', 'course_groups', 'courses', 'course_schedules', 'categories',
    'material_groups', 'materials', 'events', 'homework', 'reminders', 'notes',
)


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


def _build_legacy_note_payload(content, *, homework_id=None, event_id=None, resource_id=None, material_id=None):
    """
    Build the input dict for a legacy-content Note linked to exactly one entity. `resource_id` is
    the authoritative kwarg; `material_id` is a fallback alias for legacy callers.
    """
    payload = {'title': '', 'content': content}
    if homework_id is not None:
        payload['homework'] = [homework_id]
    if event_id is not None:
        payload['events'] = [event_id]
    resource_pk = resource_id if resource_id is not None else material_id
    if resource_pk is not None:
        payload['resources'] = [resource_pk]
    return payload


def _create_note_from_payload(payload, user, example_schedule, section):
    serializer = NoteSerializer(data=payload)
    if serializer.is_valid():
        return serializer.save(user=user, example_schedule=example_schedule)
    raise ValidationError({section: serializer.errors})


def _import_external_calendars(external_calendars, user, example_schedule):
    for external_calendar in external_calendars:
        serializer = ExternalCalendarSerializer(data=external_calendar)

        if serializer.is_valid():
            serializer.save(user=user, example_schedule=example_schedule)
        else:
            raise ValidationError({
                'external_calendars': {
                    external_calendar['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(external_calendars)} external calendars.")

    return len(external_calendars)


def _import_course_groups(course_groups, user, example_schedule):
    course_group_remap = {}

    for course_group in course_groups:
        # Field named remapped for legacy purposes
        if 'average_grade' in course_group:
            course_group['overall_grade'] = course_group['average_grade']
        serializer = CourseGroupSerializer(data=course_group)

        if serializer.is_valid():
            instance = serializer.save(user=user, example_schedule=example_schedule)
            course_group_remap[course_group['id']] = instance.pk
        else:
            raise ValidationError({
                'course_groups': {
                    course_group['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(course_groups)} course groups.")

    return course_group_remap


def _import_courses(courses, course_group_remap):
    course_remap = {}

    for course in courses:
        course_group_id = _resolve_parent(
            course_group_remap, course.get('course_group'), 'courses', 'course_group')
        course['course_group'] = course_group_id

        serializer = CourseSerializer(data=course)

        if serializer.is_valid():
            instance = serializer.save(course_group_id=course_group_id)
            course_remap[course['id']] = instance.pk
        else:
            raise ValidationError({
                'courses': {
                    course['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(courses)} courses.")

    return course_remap


def _import_course_schedules(course_schedules, course_remap):
    for course_schedule in course_schedules:
        course_id = _resolve_parent(
            course_remap, course_schedule.get('course'), 'course_schedules', 'course')
        course_schedule['course'] = course_id

        view = CourseGroupCourseCourseSchedulesApiListView()
        view.kwargs = {'course': course_id}
        context = {'view': view}
        serializer = CourseScheduleSerializer(data=course_schedule, context=context)

        if serializer.is_valid():
            serializer.save(course_id=course_id)
        else:
            raise ValidationError({
                'course_schedules': {
                    course_schedule['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(course_schedules)} course schedules.")

    return len(course_schedules)


def _import_categories(categories, request, course_remap):
    category_remap = {}

    for category in categories:
        course_id = _resolve_parent(course_remap, category.get('course'), 'categories', 'course')
        request.parser_context['kwargs']['course'] = course_id

        serializer = CategorySerializer(data=category, context={'request': request})

        if serializer.is_valid():
            instance = serializer.save(course_id=course_id)
            category_remap[category['id']] = instance.pk
        else:
            raise ValidationError({
                'categories': {
                    category['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(categories)} categories.")

    return category_remap


def _import_material_groups(material_groups, user, example_schedule):
    material_group_remap = {}

    for material_group in material_groups:
        serializer = MaterialGroupSerializer(data=material_group)

        if serializer.is_valid():
            instance = serializer.save(user=user, example_schedule=example_schedule)
            material_group_remap[material_group['id']] = instance.pk
        else:
            raise ValidationError({
                'material_groups': {
                    material_group['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(material_groups)} resource groups.")

    return material_group_remap


def _import_materials(materials, material_group_remap, course_remap, user, example_schedule):
    material_remap = {}

    for material in materials:
        if 'resource_group' in material:
            raw_group = material.get('resource_group')
            parent_key = 'resource_group'
        else:
            raw_group = material.get('material_group')
            parent_key = 'material_group'
        material_group_id = _resolve_parent(
            material_group_remap, raw_group, 'materials', parent_key)
        material['material_group'] = material_group_id
        material.pop('resource_group', None)

        courses = material.get('courses') or []
        if not isinstance(courses, list):
            raise ValidationError({'materials': "Field `courses` must be a list."})
        for i, course in enumerate(courses):
            courses[i] = _resolve_parent(course_remap, course, 'materials', 'courses')
        material['courses'] = courses

        legacy_notes_content = _extract_legacy_notes(material, legacy_field='details')
        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            instance = serializer.save(material_group_id=material_group_id)
            material_remap[material['id']] = instance.pk

            if legacy_notes_content:
                _create_note_from_payload(
                    _build_legacy_note_payload(legacy_notes_content, resource_id=instance.pk),
                    user, example_schedule, 'materials')
        else:
            raise ValidationError({
                'materials': {
                    material['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(materials)} resources.")

    return material_remap


def _import_events(events, user, example_schedule):
    event_remap = {}

    for event in events:
        legacy_notes_content = _extract_legacy_notes(event, legacy_field='comments')
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            instance = serializer.save(user=user, example_schedule=example_schedule)
            event_remap[event['id']] = instance.pk

            if legacy_notes_content:
                _create_note_from_payload(
                    _build_legacy_note_payload(legacy_notes_content, event_id=instance.pk),
                    user, example_schedule, 'events')
        else:
            raise ValidationError({
                'events': {
                    event['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(events)} events.")

    return event_remap


def _import_homework(homework, course_remap, category_remap, material_remap, user, example_schedule):
    homework_remap = {}

    for h in homework:
        course_id = _resolve_parent(course_remap, h.get('course'), 'homework', 'course')
        h['course'] = course_id

        if h.get('category'):
            h['category'] = _resolve_parent(category_remap, h.get('category'), 'homework', 'category')
        else:
            h['category'] = None

        if 'resources' in h and 'materials' in h:
            raise ValidationError(
                {'homework': "Provide either 'resources' or 'materials' on a homework row, not both."})
        field_key = 'resources' if 'resources' in h else 'materials'
        materials = h.pop('resources', None) if 'resources' in h else h.get('materials')
        materials = materials or []
        if not isinstance(materials, list):
            raise ValidationError({'homework': f"Field `{field_key}` must be a list."})
        for i, material in enumerate(materials):
            materials[i] = _resolve_parent(material_remap, material, 'homework', field_key)
        h['materials'] = materials

        legacy_notes_content = _extract_legacy_notes(h, legacy_field='comments')
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

            if legacy_notes_content:
                _create_note_from_payload(
                    _build_legacy_note_payload(legacy_notes_content, homework_id=instance.pk),
                    user, example_schedule, 'homework')
        else:
            raise ValidationError({
                'homework': {
                    h['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(homework)} homework.")

    return homework_remap


def _import_reminders(reminders, user, event_remap, homework_remap, course_remap):
    for reminder in reminders:
        reminder['homework'] = _resolve_parent(
            homework_remap, reminder.get('homework'), 'reminders', 'homework') \
            if reminder.get('homework') else None
        reminder['event'] = _resolve_parent(
            event_remap, reminder.get('event'), 'reminders', 'event') \
            if reminder.get('event') else None
        reminder['course'] = _resolve_parent(
            course_remap, reminder.get('course'), 'reminders', 'course') \
            if reminder.get('course') else None

        serializer = ReminderSerializer(data=reminder)

        if serializer.is_valid():
            serializer.save(user=user)
        else:
            raise ValidationError({
                'reminders': {
                    reminder.get('id'): serializer.errors
                }
            })

    logger.info(f"Imported {len(reminders)} reminders.")

    return len(reminders)


def _import_notes(notes, user, homework_remap, event_remap, material_remap, example_schedule):
    """
    Import notes via NoteSerializer, including those linked to entities. Handles both standalone
    notes and notes linked to homework/events/materials/resources. Entity ids are remapped to
    their newly-created values before serializer validation, so an unresolved id surfaces as a
    clean 400 rather than silently dropping the link.
    """
    notes_count = 0

    for note_data in notes:
        if not isinstance(note_data, dict):
            raise ValidationError({'notes': "Each note must be an object."})

        if 'resources' in note_data and 'materials' in note_data:
            raise ValidationError(
                {'notes': "Provide either 'resources' or 'materials' on a note, not both."})

        if 'materials' in note_data and 'resources' not in note_data:
            resources_input = note_data.get('materials', [])
        else:
            resources_input = note_data.get('resources', [])

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
                _resolve_parent(material_remap, raw_id, 'notes', 'resources')
                for raw_id in (resources_input or [])
            ],
        }

        _create_note_from_payload(payload, user, example_schedule, 'notes')
        notes_count += 1

    logger.info(f"Imported {notes_count} notes.")

    return notes_count


_SUPPRESSED_SENDERS = frozenset({Course, CourseSchedule, Category, Homework, Event})


@contextmanager
def _suppress_post_save_signals():
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


@transaction.atomic
def _bulk_import_example_schedule(data, user):
    course_group_remap = {}
    course_remap = {}
    category_remap = {}
    material_group_remap = {}
    material_remap = {}
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
    for cat in data.get('categories', []):
        instance = Category.objects.create(
            title=cat['title'],
            weight=Decimal(cat.get('weight', '0')),
            color=cat.get('color', '#000000'),
            average_grade=Decimal(cat.get('average_grade', '-1')),
            grade_by_weight=Decimal(cat.get('grade_by_weight', '0')),
            trend=cat.get('trend'),
            course_id=course_remap[cat['course']],
        )
        category_remap[cat['id']] = instance.pk

    # --- MaterialGroup ---
    for mg in _resolve_top_level_resource_groups(data):
        instance = MaterialGroup.objects.create(
            title=mg['title'],
            shown_on_calendar=mg.get('shown_on_calendar', True),
            example_schedule=True,
            user=user,
        )
        material_group_remap[mg['id']] = instance.pk

    # --- Material (with M2M courses + legacy details→notes) ---
    MaterialCourseThrough = Material.courses.through
    m2m_rows = []
    for m in _resolve_top_level_resources(data):
        raw_group = m['resource_group'] if 'resource_group' in m else m['material_group']
        instance = Material.objects.create(
            title=m['title'],
            status=m.get('status', enums.OWNED),
            condition=m.get('condition', enums.BRAND_NEW),
            website=m.get('website') or None,
            price=m.get('price', ''),
            material_group_id=material_group_remap[raw_group],
        )
        material_remap[m['id']] = instance.pk
        for course_id in [course_remap[c] for c in m.get('courses', [])]:
            m2m_rows.append(MaterialCourseThrough(material_id=instance.pk, course_id=course_id))

        legacy_content = _extract_legacy_notes(m, legacy_field='details')
        if legacy_content:
            _create_note_from_payload(
                _build_legacy_note_payload(legacy_content, resource_id=instance.pk),
                user, example_schedule=True, section='materials')

    if m2m_rows:
        MaterialCourseThrough.objects.bulk_create(m2m_rows)

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
    hw_material_m2m = []
    hw_legacy_notes = []
    for h in data.get('homework', []):
        legacy_notes_content = _extract_legacy_notes(h, legacy_field='comments')
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
        )
        instance.save()
        homework_remap[h['id']] = instance.pk
        hw_resources_field = h['resources'] if 'resources' in h else h.get('materials', [])
        hw_material_m2m.append((instance.pk, [material_remap[m] for m in hw_resources_field]))
        hw_legacy_notes.append((instance, legacy_notes_content))

    HomeworkMaterialThrough = Homework.materials.through
    hw_m2m_rows = []
    for hw_pk, material_ids in hw_material_m2m:
        for material_id in material_ids:
            hw_m2m_rows.append(HomeworkMaterialThrough(homework_id=hw_pk, material_id=material_id))
    if hw_m2m_rows:
        HomeworkMaterialThrough.objects.bulk_create(hw_m2m_rows)

    for instance, legacy_content in hw_legacy_notes:
        if legacy_content:
            _create_note_from_payload(
                _build_legacy_note_payload(legacy_content, homework_id=instance.pk),
                user, example_schedule=True, section='homework')

    # --- Reminder (individual save for start_of_range computation) ---
    for r in data.get('reminders', []):
        instance = Reminder(
            title=r['title'],
            message=r.get('message', ''),
            offset=r.get('offset', 30),
            offset_type=r.get('offset_type', enums.MINUTES),
            type=r.get('type', enums.POPUP),
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
        _import_notes(notes, user, homework_remap, event_remap, material_remap, example_schedule=True)

    metricutils.increment("user.import.schedule")

    logger.info(
        f"Bulk imported example schedule: {len(course_group_remap)} course groups, "
        f"{len(course_remap)} courses, {len(data.get('course_schedules', []))} schedules, "
        f"{len(category_remap)} categories, {len(material_group_remap)} resource groups, "
        f"{len(material_remap)} resources, {len(data.get('external_calendars', []))} external calendars, "
        f"{len(event_remap)} events, "
        f"{len(homework_remap)} homework, {len(data.get('reminders', []))} reminders, "
        f"{len(data.get('notes', []))} notes"
    )


def _resolve_top_level_resources(data):
    """
    Read the top-level resources list. `resources` is the authoritative key; `materials` is a
    permanent key-based alias. Both present is invalid.
    """
    has_resources = 'resources' in data
    has_materials = 'materials' in data

    if has_resources and has_materials:
        raise ValidationError("Provide either 'resources' or 'materials', not both.")
    if has_resources:
        return data.get('resources', []) or []
    if has_materials:
        return data.get('materials', []) or []
    return []


def _resolve_top_level_resource_groups(data):
    """
    Read the top-level resource_groups list. `resource_groups` is the authoritative key;
    `material_groups` is a permanent key-based alias. Both present is invalid.
    """
    has_resource_groups = 'resource_groups' in data
    has_material_groups = 'material_groups' in data

    if has_resource_groups and has_material_groups:
        raise ValidationError("Provide either 'resource_groups' or 'material_groups', not both.")
    if has_resource_groups:
        return data.get('resource_groups', []) or []
    if has_material_groups:
        return data.get('material_groups', []) or []
    return []


@transaction.atomic
def import_user(request, data, example_schedule=False):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param data: The data that will be imported for the user.
    """
    if not isinstance(data, dict):
        raise ValidationError("Import payload must be a JSON object.")

    materials = _resolve_top_level_resources(data)
    data['materials'] = materials

    material_groups = _resolve_top_level_resource_groups(data)
    data['material_groups'] = material_groups

    _validate_section_ids(data)

    with _suppress_post_save_signals():
        external_calendars = data.get('external_calendars', [])
        external_calendar_count = _import_external_calendars(external_calendars, request.user,
                                                             example_schedule) if external_calendars else 0

        course_groups = data.get('course_groups', [])
        course_group_remap = _import_course_groups(course_groups, request.user, example_schedule) if course_groups else {}

        courses = data.get('courses', [])
        course_remap = _import_courses(courses, course_group_remap) if courses else {}

        course_schedules = data.get('course_schedules', [])
        course_schedules_count = _import_course_schedules(course_schedules, course_remap) if course_schedules else 0

        categories = data.get('categories', [])
        category_remap = _import_categories(categories, request, course_remap) if categories else {}

        material_groups = data.get('material_groups', [])
        material_group_remap = _import_material_groups(material_groups, request.user,
                                                       example_schedule) if material_groups else {}

        material_remap = _import_materials(materials, material_group_remap, course_remap, request.user,
                                           example_schedule) if materials else {}

        events = data.get('events', [])
        event_remap = _import_events(events, request.user, example_schedule) if events else {}

        homework = data.get('homework', [])
        homework_remap = _import_homework(homework, course_remap, category_remap, material_remap, request.user,
                                          example_schedule) if homework else {}

        reminders = data.get('reminders', [])
        reminders_count = _import_reminders(reminders, request.user, event_remap, homework_remap, course_remap) if reminders else 0

        notes = data.get('notes', [])
        notes_count = _import_notes(notes, request.user, homework_remap, event_remap, material_remap,
                                    example_schedule) if notes else 0

    for course_id in set(course_remap.values()):
        taskutils.safe_apply_async(recalculate_category_grades_for_course,
            args=(course_id,), priority=settings.CELERY_PRIORITY_LOW)

    metricutils.increment("user.import.schedule")

    return (external_calendar_count, len(course_group_remap), len(course_remap), course_schedules_count,
            len(category_remap), len(material_group_remap), len(material_remap), len(event_remap), len(homework_remap),
            reminders_count, notes_count)


def _shift_datetime_to_target_date(original_dt, target_date, user_tz, all_day=False):
    """
    Shift a datetime to a new target date while preserving the local wall-clock time.

    For all-day events, wall-clock time is meaningless (the fixture's stored hour is an
    artifact of whichever timezone authored it), so midnight in the user's timezone is
    used instead.

    :param original_dt: The original aware datetime (in UTC)
    :param target_date: The target date to shift to
    :param user_tz: The user's ZoneInfo timezone
    :param all_day: If True, use midnight instead of preserving wall-clock time
    :return: New aware datetime in UTC with same local time on target date
    """
    if all_day:
        return local_midnight_as_utc(target_date, user_tz)

    local_dt = original_dt.astimezone(user_tz)
    naive_target = datetime.datetime(
        target_date.year, target_date.month, target_date.day,
        local_dt.hour, local_dt.minute, 0, 0
    )

    aware_target = naive_target.replace(tzinfo=user_tz)
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

    exceptions = reminder._parse_exceptions()
    day = min(today, course.end_date)
    day_names = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]

    while day >= course.start_date:
        if day in exceptions:
            day -= datetime.timedelta(days=1)
            continue

        weekday = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]

        active_schedule = next(
            (s for s in course_schedules if s.days_of_week[weekday] == "1"),
            None,
        )
        if active_schedule:
            start_time = getattr(active_schedule, f'{day_names[weekday]}_start_time')
            local_start = datetime.datetime.combine(day, start_time).replace(tzinfo=user_tz)

            if local_start <= now:
                return local_start.astimezone(datetime.timezone.utc)

        day -= datetime.timedelta(days=1)

    return None


def _adjust_schedule_relative_to(user, adjust_month):
    user_tz = ZoneInfo(user.settings.time_zone)
    timezone.activate(user_tz)

    now = timezone.now().astimezone(user_tz)
    adjusted_month = now.month + adjust_month
    adjusted_year = now.year
    if adjusted_month == 0:
        adjusted_month = 12
        adjusted_year -= 1

    try:
        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0, second=0,
                                     microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)
        first_monday_date = first_monday.date()

        logger.info(f'Adjusting schedule relative to new month: {adjusted_month}')
        logger.info(f'Start of week adjusted ahead {days_ahead} days')
        logger.info(f'First Monday set to {first_monday}')

        for course_group in (CourseGroup.objects.for_user(user.pk)
                .filter(example_schedule=True).iterator()):
            delta = (course_group.end_date - course_group.start_date).days
            CourseGroup.objects.filter(pk=course_group.pk).update(
                start_date=first_monday_date,
                end_date=first_monday_date + datetime.timedelta(days=delta))

        homework_to_update = []
        for homework in (Homework.objects.for_user(user.pk)
                .filter(course__course_group__example_schedule=True)
                .select_related('course')):
            course = homework.course
            start_delta = (homework.start.date() - course.start_date).days
            end_delta = (homework.end.date() - course.start_date).days
            target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
            target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

            homework.start = _shift_datetime_to_target_date(homework.start, target_start_date, user_tz,
                                                             all_day=homework.all_day)
            homework.end = _shift_datetime_to_target_date(homework.end, target_end_date, user_tz,
                                                           all_day=homework.all_day)
            homework_to_update.append(homework)

        if homework_to_update:
            Homework.objects.bulk_update(homework_to_update, ['start', 'end'])
            hw_ids_with_reminders = set(
                Reminder.objects.filter(homework__in=[h.pk for h in homework_to_update])
                .values_list('homework_id', flat=True).distinct()
            )
            for homework in homework_to_update:
                if homework.pk in hw_ids_with_reminders:
                    adjust_reminder_times(homework.pk, homework.calendar_item_type)

        first_event_start = Event.objects.for_user(user.pk).filter(example_schedule=True).first().start

        first_event_month = first_event_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_ahead = 0 - first_event_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_event_monday = first_event_month + datetime.timedelta(days_ahead)
        events_delta = (first_monday - first_event_monday).days

        events_to_update = []
        for event in (Event.objects.for_user(user.pk)
                .filter(example_schedule=True)):
            start_delta = (event.start.date() - first_monday.date()).days + events_delta
            end_delta = (event.end.date() - first_monday.date()).days + events_delta
            target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
            target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

            event.start = _shift_datetime_to_target_date(event.start, target_start_date, user_tz,
                                                          all_day=event.all_day)
            event.end = _shift_datetime_to_target_date(event.end, target_end_date, user_tz,
                                                        all_day=event.all_day)
            events_to_update.append(event)

        if events_to_update:
            Event.objects.bulk_update(events_to_update, ['start', 'end'])
            event_ids_with_reminders = set(
                Reminder.objects.filter(event__in=[e.pk for e in events_to_update])
                .values_list('event_id', flat=True).distinct()
            )
            for event in events_to_update:
                if event.pk in event_ids_with_reminders:
                    adjust_reminder_times(event.pk, event.calendar_item_type)

        for course in (Course.objects.for_user(user.pk)
                .filter(course_group__example_schedule=True).iterator()):
            delta = (course.end_date - course.start_date).days
            Course.objects.filter(pk=course.pk).update(
                start_date=first_monday_date,
                end_date=first_monday_date + datetime.timedelta(days=delta))

            coursescheduleservice.clear_cached_course_schedule(course)

        for reminder in (Reminder.objects
                .filter(course__isnull=False, sent=True, course__course_group__example_schedule=True, user=user)
                .select_related('user', 'user__settings', 'course', 'course__course_group')
                .prefetch_related('course__schedules')
                .iterator(chunk_size=2000)):
            past_start = _get_most_recent_course_occurrence_start(reminder)
            if past_start:
                offset_delta = datetime.timedelta(
                    **{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
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

        with _suppress_post_save_signals():
            _bulk_import_example_schedule(data, user)

        _adjust_schedule_relative_to(user, -1)

        for category_id in Category.objects.for_user(user.pk).values_list('pk', flat=True):
            gradingservice.recalculate_category_grade(category_id)

        course_group_ids = set()
        for course in (Course.objects.for_user(user.pk)
                .filter(course_group__example_schedule=True)
                .select_related('course_group')):
            gradingservice.recalculate_course_grade(course.pk)
            course_group_ids.add(course.course_group_id)

        for course_group_id in course_group_ids:
            gradingservice.recalculate_course_group_grade(course_group_id)
    except ValueError:
        raise ValidationError({
            'details': 'Invalid JSON.'
        })
