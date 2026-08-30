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
    """Note representation used in export bundles."""

    class Meta(NoteSerializer.Meta):
        pass


class HomeworkExportSerializer(HomeworkSerializer):
    """Homework representation used in export bundles."""

    class Meta(HomeworkSerializer.Meta):
        #: Legacy parameter, can be removed once all clients are reporting >= 3.5.0.
        fields = tuple(f for f in HomeworkSerializer.Meta.fields if f != 'comments')


class EventExportSerializer(EventSerializer):
    """Event representation used in export bundles."""

    class Meta(EventSerializer.Meta):
        #: Legacy parameter, can be removed once all clients are reporting >= 3.5.0.
        fields = tuple(f for f in EventSerializer.Meta.fields if f != 'comments')


class MaterialExportSerializer(MaterialSerializer):
    """Material representation used in export bundles."""

    class Meta(MaterialSerializer.Meta):
        #: Legacy parameter, can be removed once all clients are reporting >= 3.5.0.
        fields = tuple(f for f in MaterialSerializer.Meta.fields if f != 'details')


class ReminderExportSerializer(ReminderSerializer):
    """Reminder representation used in export bundles."""

    class Meta(ReminderSerializer.Meta):
        #: Legacy parameter, can be removed once all clients are reporting >= 3.9.0.
        fields = tuple(f for f in ReminderSerializer.Meta.fields if f != 'title')


class ExportSerializer(serializers.Serializer):
    external_calendars = ExternalCalendarSerializer(many=True)

    course_groups = CourseGroupSerializer(many=True)

    courses = CourseSerializer(many=True)

    course_schedules = CourseScheduleSerializer(many=True)

    categories = CategorySerializer(many=True)

    resource_groups = MaterialGroupSerializer(many=True)

    resources = MaterialExportSerializer(many=True)

    events = EventExportSerializer(many=True)

    homework = HomeworkExportSerializer(many=True)

    reminders = ReminderExportSerializer(many=True)

    notes = NoteExportSerializer(many=True)
