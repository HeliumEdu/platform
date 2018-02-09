import datetime
import json
import logging
import os

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.models import CourseGroup, Course, Homework, Event
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


@transaction.atomic
def import_user(request, json_str):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param json_str: The JSON string that will be parsed and imported for the user.
    """
    try:
        data = json.loads(json_str)
    except ValueError as e:
        raise ValidationError({
            'detail': e
        })

    for external_calendar in data.get('external_calendars', []):
        serializer = ExternalCalendarSerializer(data=external_calendar)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'external_calendars': {
                    external_calendar['id']: serializer.errors
                }
            })
    logger.info("Imported {} external calendars.".format(len(data.get("external_calendars", []))))

    course_group_remap = {}
    for course_group in data.get('course_groups', []):
        serializer = CourseGroupSerializer(data=course_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            course_group_remap[course_group['id']] = instance.pk
        else:
            raise ValidationError({
                'course_groups': {
                    course_group['id']: serializer.errors
                }
            })
    logger.info("Imported {} course groups.".format(len(data.get("course_groups", []))))

    course_remap = {}
    for course in data.get('courses', []):
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
    logger.info("Imported {} courses.".format(len(data.get("courses", []))))

    for course_schedule in data.get('course_schedules', []):
        course_schedule['course'] = course_remap.get(course_schedule['course'], None)

        serializer = CourseScheduleSerializer(data=course_schedule)

        if serializer.is_valid():
            serializer.save(course_id=course_schedule['course'])
        else:
            raise ValidationError({
                'course_schedules': {
                    course_schedule['id']: serializer.errors
                }
            })
    logger.info("Imported {} course schedules.".format(len(data.get("course_schedules", []))))

    category_remap = {}
    for category in data.get('categories', []):
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
    logger.info("Imported {} categories.".format(len(data.get("categories", []))))

    material_group_remap = {}
    for material_group in data.get('material_groups', []):
        serializer = MaterialGroupSerializer(data=material_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            material_group_remap[material_group['id']] = instance.pk
        else:
            raise ValidationError({
                'material_groups': {
                    material_group['id']: serializer.errors
                }
            })
    logger.info("Imported {} material groups.".format(len(data.get("material_groups", []))))

    material_remap = {}
    for material in data.get('materials', []):
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
    logger.info("Imported {} materials.".format(len(data.get("materials", []))))

    event_remap = {}
    for event in data.get('events', []):
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            event_remap[event['id']] = instance.pk
        else:
            raise ValidationError({
                'events': {
                    event['id']: serializer.errors
                }
            })
    logger.info("Imported {} events.".format(len(data.get("events", []))))

    homework_remap = {}
    for homework in data.get('homework', []):
        homework['course'] = course_remap.get(homework['course'], None)
        homework['category'] = category_remap.get(homework['category'], None) if \
            ('category' in homework and homework['category']) else None
        for i, material in enumerate(homework['materials']):
            homework['materials'][i] = material_remap.get(material, None)

        serializer = HomeworkSerializer(data=homework)

        if serializer.is_valid():
            instance = serializer.save(course_id=homework['course'])
            homework_remap[homework['id']] = instance.pk
        else:
            raise ValidationError({
                'homework': {
                    homework['id']: serializer.errors
                }
            })
    logger.info("Imported {} homework.".format(len(data.get("homework", []))))

    for reminder in data.get('reminders', []):
        reminder['homework'] = homework_remap.get(reminder['homework'], None) if \
            ('homework' in reminder and reminder['homework']) else None
        reminder['event'] = event_remap.get(reminder['event'], None) if \
            ('event' in reminder and reminder['event']) else None

        serializer = ReminderSerializer(data=reminder)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'reminders': {
                    reminder['id']: serializer.errors
                }
            })
    logger.info("Imported {} reminders.".format(len(data.get("reminders", []))))


def __adjust_schedule_relative_today(user):
    timezone.activate(user.settings.time_zone)

    start_of_current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    days_ahead = 0 - start_of_current_month.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    first_monday = start_of_current_month + datetime.timedelta(days_ahead)

    logger.info('Start of month adjusted to {}'.format(start_of_current_month))
    logger.info('Start of week adjusted ahead {} days'.format(days_ahead))
    logger.info('First Monday set to {}'.format(first_monday))

    for course_group in CourseGroup.objects.for_user(user.pk).iterator():
        delta = (course_group.end_date - course_group.start_date).days
        course_group.start_date = start_of_current_month
        course_group.end_date = start_of_current_month + datetime.timedelta(days=delta)
        course_group.save()

    for homework in Homework.objects.for_user(user.pk):
        course = homework.course
        delta = (homework.start.date() - course.start_date).days
        homework.start = (first_monday + datetime.timedelta(days=delta)).replace(
            hour=homework.start.time().hour,
            minute=homework.start.time().minute,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc)
        homework.end = (first_monday + datetime.timedelta(days=delta)).replace(
            hour=homework.end.time().hour,
            minute=homework.end.time().minute,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc)
        homework.save()

    for event in Event.objects.for_user(user.pk).iterator():
        delta = (event.start.date() - start_of_current_month).days
        event.start = (first_monday + datetime.timedelta(days=delta)).replace(
            hour=event.start.time().hour,
            minute=event.start.time().minute,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc)
        event.end = (first_monday + datetime.timedelta(days=delta)).replace(
            hour=event.end.time().hour,
            minute=event.end.time().minute,
            second=0,
            microsecond=0,
            tzinfo=timezone.utc)
        event.save()

    for course in Course.objects.for_user(user.pk):
        delta = (course.end_date - course.start_date).days
        course.start_date = start_of_current_month
        course.end_date = start_of_current_month + datetime.timedelta(days=delta)
        course.save()

    logger.info('Dates adjusted on imported example schedule relative to the start of the month for new user {}'.format(
        user.pk))

    timezone.deactivate()


def import_example_schedule(user):
    request = Request(HttpRequest(), parser_context={'kwargs': {}})
    request.user = user

    example_file = open(os.path.join(os.path.dirname(__file__), '..', 'resources', 'example_schedule.json'), 'rb')

    json_str = example_file.read()

    import_user(request, json_str)

    __adjust_schedule_relative_today(user)
