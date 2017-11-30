"""
UserSettings serializer.
"""
import logging

from rest_framework import serializers

from helium.common import enums
from helium.common.utils.commonutils import generate_random_color

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSettingsSerializer(serializers.Serializer):
    time_zone = serializers.ChoiceField(choices=enums.TIME_ZONE_CHOICES, default='America/Los_Angeles')

    default_view = serializers.ChoiceField(choices=enums.VIEW_CHOICES, default=enums.MONTH)

    week_starts_on = serializers.ChoiceField(choices=enums.DAY_OF_WEEK_CHOICES, default=enums.SUNDAY)

    all_day_offset = serializers.IntegerField(default=30)

    show_getting_started = serializers.BooleanField(default=True)

    events_color = serializers.CharField(max_length=7, default=generate_random_color)

    default_reminder_offset = serializers.IntegerField(default=30)

    default_reminder_offset_type = serializers.ChoiceField(default=enums.MINUTES,
                                                           choices=enums.REMINDER_OFFSET_TYPE_CHOICES)

    default_reminder_type = serializers.ChoiceField(default=enums.POPUP, choices=enums.REMINDER_TYPE_CHOICES)

    receive_emails_from_admin = serializers.BooleanField(default=True)

    events_private_slug = serializers.SlugField(read_only=True, required=False)

    private_slug = serializers.SlugField(read_only=True, required=False)

    def create(self, validated_data):
        """
        This method does nothing, as creationg of UserProfile and UserSettings are tightly coupled with creation of a user.
        """
        pass

    def update(self, instance, validated_data):
        """
        Update and return an existing `UserSettings` instance, given the validated data.
        """
        instance.time_zone = validated_data.get('time_zone', instance.time_zone)
        instance.default_view = validated_data.get('default_view', instance.default_view)
        instance.week_starts_on = validated_data.get('week_starts_on', instance.week_starts_on)
        instance.all_day_offset = validated_data.get('all_day_offset', instance.all_day_offset)
        instance.show_getting_started = validated_data.get('show_getting_started', instance.show_getting_started)
        instance.events_color = validated_data.get('events_color', instance.events_color)
        instance.default_reminder_offset = validated_data.get('default_reminder_offset',
                                                              instance.default_reminder_offset)
        instance.default_reminder_offset_type = validated_data.get('default_reminder_offset_type',
                                                                   instance.default_reminder_offset_type)
        instance.default_reminder_type = validated_data.get('default_reminder_type', instance.default_reminder_type)
        instance.receive_emails_from_admin = validated_data.get('receive_emails_from_admin',
                                                                instance.receive_emails_from_admin)
        instance.events_private_slug = validated_data.get('events_private_slug', instance.events_private_slug)
        instance.private_slug = validated_data.get('private_slug', instance.private_slug)

        instance.save()

        return instance
