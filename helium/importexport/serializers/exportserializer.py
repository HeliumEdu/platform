__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

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
from helium.planner.serializers.noteserializer import NoteSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

logger = logging.getLogger(__name__)


class NoteExportSerializer(NoteSerializer):
    """Note serializer for export that includes all link fields."""

    class Meta(NoteSerializer.Meta):
        # homework, events, resources are already in NoteSerializer.Meta.fields
        pass


class HomeworkExportSerializer(HomeworkSerializer):
    """Homework serializer for export that excludes legacy `comments` field."""

    class Meta(HomeworkSerializer.Meta):
        fields = tuple(f for f in HomeworkSerializer.Meta.fields if f != 'comments')


class EventExportSerializer(EventSerializer):
    """Event serializer for export that excludes legacy `comments` field."""

    class Meta(EventSerializer.Meta):
        fields = tuple(f for f in EventSerializer.Meta.fields if f != 'comments')


class MaterialExportSerializer(MaterialSerializer):
    """Material serializer for export that excludes legacy `details` field."""

    class Meta(MaterialSerializer.Meta):
        fields = tuple(f for f in MaterialSerializer.Meta.fields if f != 'details')


class ExportSerializer(serializers.Serializer):
    external_calendars = ExternalCalendarSerializer(many=True)

    course_groups = CourseGroupSerializer(many=True)

    courses = CourseSerializer(many=True)

    course_schedules = CourseScheduleSerializer(many=True)

    categories = CategorySerializer(many=True)

    material_groups = MaterialGroupSerializer(many=True)

    materials = MaterialExportSerializer(many=True)

    events = EventExportSerializer(many=True)

    homework = HomeworkExportSerializer(many=True)

    reminders = ReminderSerializer(many=True)

    notes = NoteExportSerializer(many=True)
