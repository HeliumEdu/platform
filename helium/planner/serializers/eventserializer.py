__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.22"

import logging

from rest_framework import serializers

from helium.common.utils.validators import validate_hex_color
from helium.planner.models import Event
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

logger = logging.getLogger(__name__)


class EventSerializer(serializers.ModelSerializer):
    color = serializers.CharField(max_length=7, validators=[validate_hex_color], read_only=True, required=False)
    location = serializers.CharField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'url', 'comments', 'owner_id',
            'color', 'location', 'attachments', 'reminders', 'user',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'user', 'calendar_item_type',)

    def validate(self, attrs):
        start = attrs.get('start', None)
        if not start and self.instance:
            start = self.instance.start
        end = attrs.get('end', None)
        if not end and self.instance:
            end = self.instance.end

        if start and end and start > end:
            raise serializers.ValidationError("The 'start' must be before the 'end'")

        return attrs


class EventExtendedSerializer(EventSerializer):
    attachments = AttachmentSerializer(many=True)

    reminders = ReminderSerializer(many=True)
