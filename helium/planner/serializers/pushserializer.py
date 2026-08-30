import logging

from django.db import models as django_models
from rest_framework import serializers

from helium.common.serializers.fields import TzAwareDateTimeField
from helium.planner.models import Category, Course, Event, Homework, Reminder

logger = logging.getLogger(__name__)


class BlankedField(serializers.CharField):
    """Sends an empty string in place of the stored value.

    The app needs these keys to read a reminder but never shows them on a push, and they hold text
    long enough to push a notification past what the delivery service will accept.
    """

    def __init__(self, **kwargs):
        super().__init__(read_only=True, **kwargs)

    def to_representation(self, value) -> str:
        return ''


class PushCategorySerializer(serializers.ModelSerializer):
    """Category as it appears nested in a push payload."""

    class Meta:
        model = Category
        fields = ('id', 'title', 'weight', 'average_grade', 'grade_by_weight', 'trend', 'color',
                  'course',)


class PushCourseSerializer(serializers.ModelSerializer):
    """Course as it appears nested in a push payload."""

    exceptions = BlankedField()

    class Meta:
        model = Course
        fields = ('id', 'title', 'room', 'credits', 'color', 'is_online', 'current_grade', 'trend',
                  'teacher_name', 'teacher_email', 'start_date', 'end_date', 'exceptions',
                  'course_group',)


class PushHomeworkSerializer(serializers.ModelSerializer):
    """Homework as it appears nested in a push payload."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.DateTimeField: TzAwareDateTimeField,
    }

    #: Legacy parameter, can be removed once all clients are reporting >= 3.5.0.
    comments = BlankedField()
    category = PushCategorySerializer()
    course = PushCourseSerializer()

    class Meta:
        model = Homework
        fields = ('id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority',
                  'comments', 'current_grade', 'completed', 'completed_at', 'category', 'course',
                  'calendar_item_type',)


class PushEventSerializer(serializers.ModelSerializer):
    """Event as it appears nested in a push payload."""

    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.DateTimeField: TzAwareDateTimeField,
    }

    #: Legacy parameter, can be removed once all clients are reporting >= 3.5.0.
    comments = BlankedField()

    class Meta:
        model = Event
        fields = ('id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority',
                  'comments', 'owner_id', 'user', 'recurrence_rule', 'calendar_item_type',)


class PushReminderSerializer(serializers.ModelSerializer):
    """The shape of a reminder inside a push notification payload.

    Every field a push sends is named here, rather than subtracted from the API representation.
    Adding a field to the planner API can therefore never grow a push; adding one here is a
    deliberate act, and its cost against the delivery service's size limit is the thing to check.
    """

    #: Legacy parameter, can be removed once all clients are reporting >= 3.9.0.
    title = serializers.CharField(source='message', read_only=True)

    homework = PushHomeworkSerializer()
    event = PushEventSerializer()
    course = PushCourseSerializer()

    class Meta:
        model = Reminder
        fields = ('id', 'title', 'message', 'start_of_range', 'offset', 'offset_type', 'type',
                  'sent', 'dismissed', 'homework', 'event', 'course', 'user',)
