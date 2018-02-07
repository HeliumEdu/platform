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
    data = json.loads(json_str)

    for external_calendar in data.get('external_calendars', []):
        serializer = ExternalCalendarSerializer(data=external_calendar)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'external_calendars': serializer.errors
            })

    for course_group in data.get('course_groups', []):
        serializer = CourseGroupSerializer(data=course_group)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'course_groups': serializer.errors
            })

    for course in data.get('courses', []):
        serializer = CourseSerializer(data=course)

        if serializer.is_valid():
            serializer.save(course_group_id=course['course_group'])
        else:
            raise ValidationError({
                'courses': serializer.errors
            })

    for category in data.get('categories', []):
        request.parser_context['kwargs']['course'] = category['course']
        serializer = CategorySerializer(data=category, context={'request': request})

        if serializer.is_valid():
            serializer.save(course_id=category['course'])
        else:
            raise ValidationError({
                'categories': serializer.errors
            })

    for material_group in data.get('material_groups', []):
        serializer = MaterialGroupSerializer(data=material_group)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'material_groups': serializer.errors
            })

    for material in data.get('materials', []):
        serializer = MaterialSerializer(data=material)

        if serializer.is_valid():
            serializer.save(material_group_id=material['material_group'])
        else:
            raise ValidationError({
                'material_groups': serializer.errors
            })

    for event in data.get('events', []):
        serializer = EventSerializer(data=event)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'events': serializer.errors
            })

    for homework in data.get('homework', []):
        serializer = HomeworkSerializer(data=homework)

        if serializer.is_valid():
            serializer.save(course_id=homework['course'])
        else:
            raise ValidationError({
                'homework': serializer.errors
            })

    for reminder in data.get('reminders', []):
        serializer = ReminderSerializer(data=reminder)

        if serializer.is_valid():
            serializer.save(user=request.user)
        else:
            raise ValidationError({
                'reminders': serializer.errors
            })
