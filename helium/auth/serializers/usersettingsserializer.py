"""
UserSettings serializer.
"""
import logging

from rest_framework import serializers

from helium.auth.models import UserSettings

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'time_zone', 'default_view', 'week_starts_on', 'all_day_offset', 'show_getting_started', 'events_color',
            'default_reminder_offset', 'default_reminder_offset_type', 'default_reminder_type', 'receive_emails_from_admin',
            'events_private_slug', 'private_slug', 'user',)
        read_only_fields = ('events_private_slug', 'private_slug', 'user',)
