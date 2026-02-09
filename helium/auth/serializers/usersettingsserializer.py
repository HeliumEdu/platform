__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.auth.models import UserSettings

logger = logging.getLogger(__name__)


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'time_zone', 'default_view', 'week_starts_on', 'all_day_offset', 'show_getting_started',
            'whats_new_version_seen', 'events_color', 'grade_color', 'material_color', 'remember_filter_state',
            'color_scheme_theme', 'calendar_event_limit', 'default_reminder_type', 'default_reminder_offset',
            'default_reminder_offset_type', 'calendar_use_category_colors', 'receive_emails_from_admin',
            'private_slug', 'user',)
        read_only_fields = ('all_day_offset', 'private_slug', 'user',)
