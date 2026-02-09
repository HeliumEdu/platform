__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import Reminder, Homework, Event

logger = logging.getLogger(__name__)


class ReminderSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['homework'].queryset = Homework.objects.for_user(self.context['request'].user.pk)
            self.fields['event'].queryset = Event.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Reminder
        fields = (
            'id', 'title', 'message', 'start_of_range', 'offset', 'offset_type', 'type', 'sent', 'dismissed',
            'homework', 'event', 'user',)
        read_only_fields = ('start_of_range', 'user',)

    def validate(self, attrs):
        if not self.instance and ('event' not in attrs and 'homework' not in attrs):
            raise serializers.ValidationError("One of `event` or `homework` must be given.")
        elif attrs.get('event', None) and attrs.get('homework', None):
            raise serializers.ValidationError("Only one of `event` or `homework` may be given.")

        # We're settings these to None here as the serialization save will persist the new parent
        if self.instance and ('event' in attrs or 'homework' in attrs):
            self.instance.event = None
            self.instance.homework = None

        return attrs


class ReminderExtendedSerializer(ReminderSerializer):
    def to_representation(self, instance):
        # Import serializers here to avoid circular imports
        from helium.planner.serializers.homeworkserializer import HomeworkSerializer
        from helium.planner.serializers.eventserializer import EventSerializer

        # Get base representation first
        representation = super().to_representation(instance)

        # Serialize homework and event with their respective serializers if present
        if instance.homework:
            homework_serializer = HomeworkSerializer(instance.homework, context=self.context)
            representation['homework'] = homework_serializer.data

        if instance.event:
            event_serializer = EventSerializer(instance.event, context=self.context)
            representation['event'] = event_serializer.data

        # Keep only the user ID instead of the full nested user object
        representation['user'] = instance.user.id

        return representation
