__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import logging
import os

import pytz
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from helium.common.utils import metricutils
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.models import CourseGroup, Course, Homework, Event, Category, Note
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.services import coursescheduleservice
from helium.planner.services import reminderservice
from helium.planner.tasks import adjust_reminder_times, recalculate_category_grade
from helium.planner.utils.quillutils import html_to_quill
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiListView

logger = logging.getLogger(__name__)


def _extract_legacy_notes(data, legacy_field='comments'):
    """
    Extract and convert legacy HTML notes field to Quill JSON format.

    Removes the legacy field from data and returns the converted Quill JSON content.
    Returns None if no legacy content or conversion fails.

    :param data: The entity data dict (modified in place to remove legacy field)
    :param legacy_field: The name of the legacy field ('comments' or 'details')
    :return: Quill JSON content dict or None
    """
    legacy_content = data.pop(legacy_field, None)

    if legacy_content:
        return html_to_quill(legacy_content)

    return None


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
        course['course_group'] = course_group_remap.get(course['course_group'], None)

        serializer = CourseSerializer(data=course)

        if serializer.is_valid():
            instance = serializer.save(course_group_id=course['course_group'])
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
        course_schedule['course'] = course_remap.get(course_schedule['course'], None)

        view = CourseGroupCourseCourseSchedulesApiListView()
        view.kwargs = {'course': course_schedule['course']}
        context = {'view': view}
        serializer = CourseScheduleSerializer(data=course_schedule, context=context)

        if serializer.is_valid():
            serializer.save(course_id=course_schedule['course'])
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
        request.parser_context['kwargs']['course'] = course_remap.get(category['course'], None)

        serializer = CategorySerializer(data=category, context={'request': request})

        if serializer.is_valid():
            instance = serializer.save(course_id=course_remap.get(category['course'], None))
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

    logger.info(f"Imported {len(material_groups)} material groups.")

    return material_group_remap


def _import_materials(materials, material_group_remap, course_remap, user, example_schedule):
    material_remap = {}

    for material in materials:
        material['material_group'] = material_group_remap.get(material['material_group'], None)
        for i, course in enumerate(material['courses']):
            material['courses'][i] = course_remap.get(course, None)

        legacy_notes_content = _extract_legacy_notes(material, legacy_field='details')
        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            instance = serializer.save(material_group_id=material['material_group'])
            material_remap[material['id']] = instance.pk

            if legacy_notes_content:
                note = Note.objects.create(
                    title='',
                    content=legacy_notes_content,
                    user=user,
                    example_schedule=example_schedule,
                )
                note.resources.add(instance)
        else:
            raise ValidationError({
                'materials': {
                    material['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(materials)} materials.")

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
                note = Note.objects.create(
                    title='',
                    content=legacy_notes_content,
                    user=user,
                    example_schedule=example_schedule,
                )
                note.events.add(instance)
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
        h['course'] = course_remap.get(h['course'], None)
        h['category'] = category_remap.get(h['category'], None) if \
            ('category' in h and h['category']) else None
        for i, material in enumerate(h['materials']):
            h['materials'][i] = material_remap.get(material, None)

        legacy_notes_content = _extract_legacy_notes(h, legacy_field='comments')
        serializer = HomeworkSerializer(data=h)

        if serializer.is_valid():
            instance = serializer.save(course_id=h['course'])
            homework_remap[h['id']] = instance.pk

            if legacy_notes_content:
                note = Note.objects.create(
                    title='',
                    content=legacy_notes_content,
                    user=user,
                    example_schedule=example_schedule,
                )
                note.homework.add(instance)
        else:
            raise ValidationError({
                'homework': {
                    h['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(homework)} homework.")

    return homework_remap


def _import_reminders(reminders, user, event_remap, homework_remap):
    for reminder in reminders:
        reminder['homework'] = homework_remap.get(reminder['homework'], None) if \
            ('homework' in reminder and reminder['homework']) else None
        reminder['event'] = event_remap.get(reminder['event'], None) if \
            ('event' in reminder and reminder['event']) else None

        serializer = ReminderSerializer(data=reminder)

        if serializer.is_valid():
            serializer.save(user=user)
        else:
            raise ValidationError({
                'reminders': {
                    reminder['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(reminders)} reminders.")

    return len(reminders)


def _import_notes(notes, user, homework_remap, event_remap, material_remap, example_schedule):
    """Import notes, including those linked to entities.

    Handles both standalone notes and notes linked to homework/events/materials.
    For linked notes, the entity IDs are remapped to their new values.
    """
    notes_count = 0

    for note_data in notes:
        note = Note.objects.create(
            title=note_data.get('title', ''),
            content=note_data.get('content', {}),
            user=user,
            example_schedule=example_schedule,
        )

        for old_hw_id in note_data.get('homework', []):
            new_hw_id = homework_remap.get(old_hw_id)
            if new_hw_id:
                note.homework.add(new_hw_id)

        for old_event_id in note_data.get('events', []):
            new_event_id = event_remap.get(old_event_id)
            if new_event_id:
                note.events.add(new_event_id)

        for old_material_id in note_data.get('resources', []):
            new_material_id = material_remap.get(old_material_id)
            if new_material_id:
                note.resources.add(new_material_id)

        notes_count += 1

    logger.info(f"Imported {notes_count} notes.")

    return notes_count


@transaction.atomic
def import_user(request, data, example_schedule=False):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param data: The data that will be imported for the user.
    """
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

    materials = data.get('materials', [])
    material_remap = _import_materials(materials, material_group_remap, course_remap, request.user,
                                       example_schedule) if materials else {}

    events = data.get('events', [])
    event_remap = _import_events(events, request.user, example_schedule) if events else {}

    homework = data.get('homework', [])
    homework_remap = _import_homework(homework, course_remap, category_remap, material_remap, request.user,
                                      example_schedule) if homework else {}

    reminders = data.get('reminders', [])
    reminders_count = _import_reminders(reminders, request.user, event_remap, homework_remap) if reminders else 0

    notes = data.get('notes', [])
    notes_count = _import_notes(notes, request.user, homework_remap, event_remap, material_remap,
                                example_schedule) if notes else 0

    metricutils.increment("user.import.schedule")

    return (external_calendar_count, len(course_group_remap), len(course_remap), course_schedules_count,
            len(category_remap), len(material_group_remap), len(material_remap), len(event_remap), len(homework_remap),
            reminders_count, notes_count)


def _shift_datetime_to_target_date(original_dt, target_date, user_tz):
    """
    Shift a datetime to a new target date while preserving the local wall-clock time.
    Uses pytz to handle DST transitions automatically.

    :param original_dt: The original aware datetime (in UTC)
    :param target_date: The target date to shift to
    :param user_tz: The user's pytz timezone
    :return: New aware datetime in UTC with same local time on target date
    """
    # Convert to user's local time to get the wall-clock hour/minute
    local_dt = original_dt.astimezone(user_tz)

    # Create a naive datetime on the target date with the same local hour/minute
    naive_target = datetime.datetime(
        target_date.year, target_date.month, target_date.day,
        local_dt.hour, local_dt.minute, 0, 0
    )

    # Localize to user's timezone (pytz handles DST automatically)
    aware_target = user_tz.localize(naive_target)

    # Convert back to UTC for storage
    return aware_target.astimezone(pytz.UTC)


def _adjust_schedule_relative_to(user, adjust_month):
    user_tz = pytz.timezone(user.settings.time_zone)
    timezone.activate(user_tz)

    now = timezone.now()
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

        for homework in (Homework.objects.for_user(user.pk)
                .filter(course__course_group__example_schedule=True)
                .select_related('course')
                .iterator()):
            course = homework.course
            start_delta = (homework.start.date() - course.start_date).days
            end_delta = (homework.end.date() - course.start_date).days
            target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
            target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

            new_start = _shift_datetime_to_target_date(homework.start, target_start_date, user_tz)
            new_end = _shift_datetime_to_target_date(homework.end, target_end_date, user_tz)

            Homework.objects.filter(pk=homework.pk).update(start=new_start, end=new_end)
            adjust_reminder_times(homework.pk, homework.calendar_item_type)

        first_event_start = Event.objects.for_user(user.pk).filter(example_schedule=True).first().start

        first_event_month = first_event_start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_ahead = 0 - first_event_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_event_monday = first_event_month + datetime.timedelta(days_ahead)
        events_delta = (first_monday - first_event_monday).days

        for event in (Event.objects.for_user(user.pk)
                .filter(example_schedule=True).iterator()):
            start_delta = (event.start.date() - first_monday.date()).days + events_delta
            end_delta = (event.end.date() - first_monday.date()).days + events_delta
            target_start_date = first_monday_date + datetime.timedelta(days=start_delta)
            target_end_date = first_monday_date + datetime.timedelta(days=end_delta)

            new_start = _shift_datetime_to_target_date(event.start, target_start_date, user_tz)
            new_end = _shift_datetime_to_target_date(event.end, target_end_date, user_tz)

            Event.objects.filter(pk=event.pk).update(start=new_start, end=new_end)
            adjust_reminder_times(event.pk, event.calendar_item_type)

        for course in (Course.objects.for_user(user.pk)
                .filter(course_group__example_schedule=True).iterator()):
            delta = (course.end_date - course.start_date).days
            Course.objects.filter(pk=course.pk).update(
                start_date=first_monday_date,
                end_date=first_monday_date + datetime.timedelta(days=delta))

            coursescheduleservice.clear_cached_course_schedule(course)

        logger.info(
            f'Dates adjusted on imported example schedule relative to the start of the month for new user {user.pk}')
    except Exception:
        logger.error("An error occurred adjusting example schedule dates.", exc_info=True)

    timezone.deactivate()


def import_example_schedule(user):
    request = Request(HttpRequest(), parser_context={'kwargs': {}})
    request.user = user

    example_file = open(os.path.join(os.path.dirname(__file__), '..', 'resources', 'example_schedule.json'), 'rb')

    json_str = example_file.read().decode('utf-8')
    try:
        data = json.loads(json_str)

        import_user(request, data, True)

        _adjust_schedule_relative_to(user, -1)

        reminderservice.process_push_reminders(True)

        for category in Category.objects.for_user(user.pk).iterator():
            recalculate_category_grade.apply_async(
                args=(category.pk,), priority=settings.CELERY_PRIORITY_LOW
            )
    except ValueError:
        raise ValidationError({
            'details': 'Invalid JSON.'
        })
