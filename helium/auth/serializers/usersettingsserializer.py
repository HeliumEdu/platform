import logging

from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from helium.auth.models import UserSettings
from helium.common.utils.validators import validate_hex_color

logger = logging.getLogger(__name__)


#: Legacy parameter, can be removed once all clients are reporting >= 3.9.4.
@extend_schema_serializer(exclude_fields=('material_color',))
class UserSettingsSerializer(serializers.ModelSerializer):
    #: Once all backend code has been factored from Material terminology to Resource terminology, including data model changes and migrations, this line can be removed.
    resource_color = serializers.CharField(
        source='material_color', required=False, max_length=7, validators=[validate_hex_color],
        help_text='A valid hex color code choice to determine the color resource badges will be.')

    class Meta:
        model = UserSettings
        fields = (
            'time_zone', 'default_view', 'week_starts_on', 'show_getting_started',
            'is_setup_complete', 'whats_new_version_seen', 'events_color', 'grade_color', 'material_color',
            'resource_color', 'remember_filter_state', 'color_scheme_theme', 'calendar_event_limit',
            'default_reminder_type', 'default_reminder_offset', 'default_reminder_offset_type',
            'calendar_use_category_colors', 'show_planner_tooltips', 'drag_and_drop_on_mobile', 'at_risk_threshold',
            'on_track_tolerance', 'show_week_numbers', 'receive_emails_from_admin', 'private_slug', 'user',
            'prompt_for_review',)
        read_only_fields = ('is_setup_complete', 'private_slug', 'user',
                            'prompt_for_review',)


#: Legacy 'show_getting_started' parameter, can be removed once all clients are reporting >= 3.9.4, after which it becomes a read-only field above.
#: Legacy 'material_color' parameter, can be removed once all clients are reporting >= 3.9.4.
@extend_schema_serializer(exclude_fields=('show_getting_started', 'material_color'), component_name='UserSettingsUpdate')
class UserSettingsUpdateSerializer(UserSettingsSerializer):
    pass
