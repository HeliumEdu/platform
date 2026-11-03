import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
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

logger = logging.getLogger(__name__)


class NoteExportSerializer(NoteSerializer):
    """Note representation used in export bundles."""

    class Meta(NoteSerializer.Meta):
        pass


class HomeworkExportSerializer(HomeworkSerializer):
    """Homework representation used in export bundles."""


class EventExportSerializer(EventSerializer):
    """Event representation used in export bundles."""


@extend_schema_serializer(component_name='ResourceExport')
class ResourceExportSerializer(ResourceSerializer):
    """Resource representation used in export bundles."""


class ReminderExportSerializer(ReminderSerializer):
    """Reminder representation used in export bundles."""


class ExportSerializer(serializers.Serializer):
    external_calendars = ExternalCalendarSerializer(many=True)

    course_groups = CourseGroupSerializer(many=True)

    courses = CourseSerializer(many=True)

    course_schedules = CourseScheduleSerializer(many=True)

    categories = CategorySerializer(many=True)

    resource_groups = ResourceGroupSerializer(many=True)

    resources = ResourceExportSerializer(many=True)

    events = EventExportSerializer(many=True)

    homework = HomeworkExportSerializer(many=True)

    reminders = ReminderExportSerializer(many=True)

    notes = NoteExportSerializer(many=True)
