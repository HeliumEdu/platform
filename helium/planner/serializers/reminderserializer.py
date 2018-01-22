import logging

from rest_framework import serializers

from helium.planner.models import Reminder

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = (
            'id', 'title', 'message', 'start_of_range', 'offset', 'offset_type', 'type', 'sent', 'from_admin',
            'homework', 'event', 'user',)
        read_only_fields = ('from_admin', 'user',)

    def validate(self, attrs):
        if not self.instance and ('event' not in attrs and 'homework' not in attrs):
            raise serializers.ValidationError("At least one of `event` or `homework` must be given.")

        return attrs


class ReminderExtendedSerializer(ReminderSerializer):
    class Meta(ReminderSerializer.Meta):
        depth = 2
