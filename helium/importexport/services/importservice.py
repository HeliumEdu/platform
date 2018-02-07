import json
import logging

from django.db import transaction
from rest_framework.exceptions import ValidationError

from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.materialgroupserializer import MaterialGroupSerializer
from helium.planner.serializers.materialserializer import MaterialSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

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
                'external_calendars': serializer.errors
            })

    course_group_remap = {}
    for course_group in data.get('course_groups', []):
        serializer = CourseGroupSerializer(data=course_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            course_group_remap[course_group['id']] = instance.pk
        else:
            raise ValidationError({
                'course_groups': serializer.errors
            })

    course_remap = {}
    for course in data.get('courses', []):
        serializer = CourseSerializer(data=course)

        if serializer.is_valid():
            instance = serializer.save(course_group_id=course_group_remap.get(course['course_group'], None))
            course_remap[course['id']] = instance.pk
        else:
            raise ValidationError({
                'courses': serializer.errors
            })

    category_remap = {}
    for category in data.get('categories', []):
        request.parser_context['kwargs']['course'] = course_remap.get(category['course'], None)
        serializer = CategorySerializer(data=category, context={'request': request})

        if serializer.is_valid():
            instance = serializer.save(course_id=course_remap.get(category['course'], None))
            category_remap[category['id']] = instance.pk
        else:
            raise ValidationError({
                'categories': serializer.errors
            })

    material_group_remap = {}
    for material_group in data.get('material_groups', []):
        serializer = MaterialGroupSerializer(data=material_group)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            material_group_remap[material_group['id']] = instance.pk
        else:
            raise ValidationError({
                'material_groups': serializer.errors
            })

    material_remap = {}
    for material in data.get('materials', []):
        for i, course in enumerate(material['courses']):
            material['courses'][i] = course_remap.get(course, None)

        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            instance = serializer.save(material_group_id=material_group_remap.get(material['material_group'], None))
            material_remap[material['id']] = instance.pk
        else:
            raise ValidationError({
                'material_groups': serializer.errors
            })

    event_remap = {}
    for event in data.get('events', []):
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            instance = serializer.save(user=request.user)
            event_remap[event['id']] = instance.pk
        else:
            raise ValidationError({
                'events': serializer.errors
            })

    homework_remap = {}
    for homework in data.get('homework', []):
        for i, material in enumerate(homework['materials']):
            homework['materials'][i] = material_remap.get(material, None)

        homework['category'] = category_remap.get(homework['category'], None) if \
            ('category' in homework and homework['category']) else None
        serializer = HomeworkSerializer(data=homework)

        if serializer.is_valid():
            instance = serializer.save(course_id=course_remap.get(homework['course'], None))
            homework_remap[homework['id']] = instance.pk
        else:
            raise ValidationError({
                'homework': serializer.errors
            })

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
                'reminders': serializer.errors
            })
