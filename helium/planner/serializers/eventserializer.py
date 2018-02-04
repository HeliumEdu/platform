import logging

from rest_framework import serializers

from helium.planner.models import Event

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'

logger = logging.getLogger(__name__)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'url', 'comments', 'attachments',
            'reminders', 'user',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'user', 'calendar_item_type',)

    def validate(self, attrs):
        start = self.instance.start if self.instance else attrs.get('start', None)
        end = self.instance.end if self.instance else attrs.get('end', None)

        if start and end and start > end:
            raise serializers.ValidationError("The 'start' must be before the 'end'")

        return attrs


class EventExtendedSerializer(EventSerializer):
    class Meta(EventSerializer.Meta):
        depth = 1
