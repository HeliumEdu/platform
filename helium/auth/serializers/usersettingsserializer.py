__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from helium.auth.models import UserSettings

logger = logging.getLogger(__name__)


class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'time_zone', 'default_view', 'week_starts_on', 'all_day_offset', 'show_getting_started',
            'is_setup_complete', 'whats_new_version_seen', 'events_color', 'grade_color', 'material_color',
            'remember_filter_state', 'color_scheme_theme', 'calendar_event_limit', 'default_reminder_type',
            'default_reminder_offset', 'default_reminder_offset_type', 'calendar_use_category_colors',
            'show_planner_tooltips', 'drag_and_drop_on_mobile', 'at_risk_threshold',
            'on_track_tolerance', 'show_week_numbers',
            'receive_emails_from_admin', 'private_slug', 'user',
            'prompt_for_review', 'next_review_prompt_date', 'review_prompts_shown',)
        read_only_fields = ('all_day_offset', 'is_setup_complete', 'private_slug', 'user',
                            'next_review_prompt_date',)

    def update(self, instance, validated_data):
        if 'review_prompts_shown' in validated_data:
            validated_data['next_review_prompt_date'] = (
                timezone.now() + timedelta(days=settings.REVIEW_PROMPT_COOLDOWN_DAYS)
            )
        return super().update(instance, validated_data)
