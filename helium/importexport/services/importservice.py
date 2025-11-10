__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.21"

import datetime
import json
import logging
import os

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from helium.common.utils import metricutils
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.models import CourseGroup, Course, Homework, Event, Category
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
from helium.planner.tasks import adjust_reminder_times, recalculate_category_grade
from helium.planner.views.apis.coursescheduleviews import CourseGroupCourseCourseSchedulesApiListView

logger = logging.getLogger(__name__)


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


def _import_materials(materials, material_group_remap, course_remap):
    material_remap = {}

    for material in materials:
        material['material_group'] = material_group_remap.get(material['material_group'], None)
        for i, course in enumerate(material['courses']):
            material['courses'][i] = course_remap.get(course, None)

        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            instance = serializer.save(material_group_id=material['material_group'])
            material_remap[material['id']] = instance.pk
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
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            instance = serializer.save(user=user, example_schedule=example_schedule)
            event_remap[event['id']] = instance.pk
        else:
            raise ValidationError({
                'events': {
                    event['id']: serializer.errors
                }
            })

    logger.info(f"Imported {len(events)} events.")

    return event_remap


def _import_homework(homework, course_remap, category_remap, material_remap):
    homework_remap = {}

    for h in homework:
        h['course'] = course_remap.get(h['course'], None)
        h['category'] = category_remap.get(h['category'], None) if \
            ('category' in h and h['category']) else None
        for i, material in enumerate(h['materials']):
            h['materials'][i] = material_remap.get(material, None)

        serializer = HomeworkSerializer(data=h)

        if serializer.is_valid():
            instance = serializer.save(course_id=h['course'])
            homework_remap[h['id']] = instance.pk
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


@transaction.atomic
def import_user(request, data, example_schedule=False):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param data: The data that will be imported for the user.
    """
    external_calendar_count = _import_external_calendars(data.get('external_calendars', []), request.user, example_schedule)

    course_group_remap = _import_course_groups(data.get('course_groups', []), request.user, example_schedule)

    course_remap = _import_courses(data.get('courses', []), course_group_remap)

    course_schedules_count = _import_course_schedules(data.get('course_schedules', []), course_remap)

    category_remap = _import_categories(data.get('categories', []), request, course_remap)

    material_group_remap = _import_material_groups(data.get('material_groups', []), request.user, example_schedule)

    material_remap = _import_materials(data.get('materials', []), material_group_remap, course_remap)

    event_remap = _import_events(data.get('events', []), request.user, example_schedule)

    homework_remap = _import_homework(data.get('homework', []), course_remap, category_remap, material_remap)

    reminders_count = _import_reminders(data.get('reminders', []), request.user, event_remap, homework_remap)

    metricutils.increment("user.import.schedule")

    return (external_calendar_count, len(course_group_remap), len(course_remap), course_schedules_count,
            len(category_remap), len(material_group_remap), len(material_remap), len(event_remap), len(homework_remap),
            reminders_count)


def _adjust_schedule_relative_to(user, month):
    timezone.activate(user.settings.time_zone)

    try:
        adjusted_month = timezone.now().replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)

        logger.info(f'Adjusting schedule relative to new month: {month}')
        logger.info(f'Start of week adjusted ahead {days_ahead} days')
        logger.info(f'First Monday set to {first_monday}')

        for course_group in CourseGroup.objects.for_user(user.pk).iterator():
            delta = (course_group.end_date - course_group.start_date).days
            CourseGroup.objects.filter(pk=course_group.pk).update(
                start_date=first_monday,
                end_date=first_monday + datetime.timedelta(days=delta))

        for homework in Homework.objects.for_user(user.pk).iterator():
            course = homework.course
            delta = (homework.start.date() - course.start_date).days
            Homework.objects.filter(pk=homework.pk).update(
                start=(first_monday + datetime.timedelta(days=delta)).replace(
                    hour=homework.start.time().hour,
                    minute=homework.start.time().minute,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc),
                end=(first_monday + datetime.timedelta(days=delta)).replace(
                    hour=homework.end.time().hour,
                    minute=homework.end.time().minute,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc))

            adjust_reminder_times.delay(homework.pk, homework.calendar_item_type)

        for event in Event.objects.for_user(user.pk).iterator():
            adjusted_month = event.start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            delta = (event.start.date() - adjusted_month.date()).days
            Event.objects.filter(pk=event.pk).update(
                start=(first_monday + datetime.timedelta(days=delta)).replace(
                    hour=event.start.time().hour,
                    minute=event.start.time().minute,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc),
                end=(first_monday + datetime.timedelta(days=delta)).replace(
                    hour=event.end.time().hour,
                    minute=event.end.time().minute,
                    second=0,
                    microsecond=0,
                    tzinfo=timezone.utc))

            adjust_reminder_times.delay(event.pk, event.calendar_item_type)

        for course in Course.objects.for_user(user.pk).iterator():
            delta = (course.end_date - course.start_date).days
            Course.objects.filter(pk=course.pk).update(
                start_date=first_monday,
                end_date=first_monday + datetime.timedelta(days=delta))

            coursescheduleservice.clear_cached_course_schedule(course)

        logger.info(
            f'Dates adjusted on imported example schedule relative to the start of the month for new user {user.pk}')
    except:
        logger.error("An unknown error occurred.", exc_info=True)

    timezone.deactivate()


def import_example_schedule(user):
    request = Request(HttpRequest(), parser_context={'kwargs': {}})
    request.user = user

    example_file = open(os.path.join(os.path.dirname(__file__), '..', 'resources', 'example_schedule.json'), 'rb')

    json_str = example_file.read().decode('utf-8')
    try:
        data = json.loads(json_str)

        import_user(request, data, True)

        adjusted_month = timezone.now().month - 1
        if adjusted_month == 0:
            adjusted_month = 12
        _adjust_schedule_relative_to(user, adjusted_month)

        for category in Category.objects.for_user(user.pk).iterator():
            recalculate_category_grade.delay(category.pk)
    except ValueError:
        raise ValidationError({
            'details': 'Invalid JSON.'
        })
