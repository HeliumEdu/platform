import logging

from django.utils import timezone
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.auth.models import UserSettings
from helium.common.utils.validators import validate_hex_color

logger = logging.getLogger(__name__)


class UserSettingsSerializer(serializers.ModelSerializer):
    getting_started_due = serializers.BooleanField(
        required=False,
        help_text='Whether the "Getting Started" dialog should be shown now. Set to false once it has been shown.')

    resource_color = serializers.CharField(
        required=False, max_length=7, validators=[validate_hex_color],
        help_text='A valid hex color code choice to determine the color resource badges will be.')

    class Meta:
        model = UserSettings
        fields = (
            'time_zone', 'default_view', 'week_starts_on', 'show_getting_started', 'getting_started_due',
            'setup_state', 'whats_new_version_seen', 'events_color', 'grade_color',
            'resource_color', 'remember_filter_state', 'color_scheme_theme', 'calendar_event_limit',
            'default_reminder_type', 'default_reminder_offset', 'default_reminder_offset_type',
            'calendar_use_category_colors', 'show_planner_tooltips', 'drag_and_drop_on_mobile', 'at_risk_threshold',
            'on_track_tolerance', 'show_week_numbers', 'date_format', 'time_format', 'number_format',
            'receive_emails_from_admin', 'private_slug', 'user', 'prompt_for_review',)
        read_only_fields = ('show_getting_started', 'setup_state', 'private_slug', 'user',
                            'prompt_for_review',)

    def update(self, instance, validated_data):
        if validated_data.pop('getting_started_due', True) is False:
            instance.getting_started_last_shown_at = timezone.now()

        return super().update(instance, validated_data)


@extend_schema_serializer(component_name='UserSettingsUpdate')
class UserSettingsUpdateSerializer(UserSettingsSerializer):
    pass
