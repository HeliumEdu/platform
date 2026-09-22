import logging

from django.db import models as django_models
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.common import enums
from helium.common.serializers.fields import ExceptionDatesField, TzAwareDateTimeField
from helium.common.utils.validators import (
    infer_byday_for_weekly_rrule,
    validate_hex_color,
    validate_recurrence_rule,
)
from helium.planner.models import Event
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

logger = logging.getLogger(__name__)


#: Permanently excluded: `comments` is only populated on the synthesised external calendar and
#: course schedule events that inherit this serializer, never on a stored Event.
@extend_schema_serializer(exclude_fields=('comments',))
class EventSerializer(serializers.ModelSerializer):
    serializer_field_mapping = {
        **serializers.ModelSerializer.serializer_field_mapping,
        django_models.DateTimeField: TzAwareDateTimeField,
    }

    color = serializers.CharField(max_length=7, validators=[validate_hex_color], read_only=True, required=False)
    location = serializers.CharField(read_only=True, required=False, allow_null=True)
    exception_dates = ExceptionDatesField(required=False, allow_null=True)
    notes = serializers.PrimaryKeyRelatedField(source='notes_set', many=True, read_only=True)
    calendar_item_type = serializers.ChoiceField(choices=enums.CALENDAR_ITEM_TYPE_CHOICES, read_only=True,
                                                 help_text='Which kind of calendar item this is; a client can key rendering off it without inspecting the URL it came from.')

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'url', 'comments',
            'owner_id',
            'color', 'location', 'attachments', 'reminders', 'notes', 'user',
            'recurrence_rule', 'exception_dates',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'notes', 'user', 'calendar_item_type',)
        extra_kwargs = {
            'recurrence_rule': {'validators': [validate_recurrence_rule]},
        }

    def validate(self, attrs):
        start = attrs.get('start', None)
        if not start and self.instance:
            start = self.instance.start
        end = attrs.get('end', None)
        if not end and self.instance:
            end = self.instance.end

        if start and end and start > end:
            raise serializers.ValidationError("The 'start' must be before the 'end'")

        if 'recurrence_rule' in attrs and attrs['recurrence_rule'] and start:
            attrs['recurrence_rule'] = infer_byday_for_weekly_rrule(attrs['recurrence_rule'], start)

        return attrs


#: Permanently excluded: `comments` is only populated on the synthesised external calendar and
#: course schedule events that inherit this serializer, never on a stored Event.
@extend_schema_serializer(exclude_fields=('comments',))
class EventExtendedSerializer(EventSerializer):
    attachments = AttachmentSerializer(many=True)

    reminders = ReminderSerializer(many=True)

class GeneratedEventSerializer(EventSerializer):
    """
    An event generated on the fly rather than stored, which owns none of the relations a
    saved event can.

    Course schedules and external calendars both synthesise events in memory and never save
    them, so nothing can reference one. The deterministic id each carries is non-null though,
    so Django would query for those relations on its behalf regardless.
    """

    attachments = serializers.SerializerMethodField()
    reminders = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    def get_attachments(self, obj) -> list:
        return []

    def get_reminders(self, obj) -> list:
        return []

    def get_notes(self, obj) -> list:
        return []
