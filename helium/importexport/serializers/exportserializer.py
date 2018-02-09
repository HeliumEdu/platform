import logging

from rest_framework import serializers

from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
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


class ExportSerializer(serializers.Serializer):
    external_calendars = ExternalCalendarSerializer(many=True)

    course_groups = CourseGroupSerializer(many=True)

    courses = CourseSerializer(many=True)

    course_schedules = CourseScheduleSerializer(many=True)

    categories = CategorySerializer(many=True)

    material_groups = MaterialGroupSerializer(many=True)

    materials = MaterialSerializer(many=True)

    events = EventSerializer(many=True)

    homework = HomeworkSerializer(many=True)

    reminders = ReminderSerializer(many=True)
