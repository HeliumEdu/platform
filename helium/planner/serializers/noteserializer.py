__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models import Note

logger = logging.getLogger(__name__)


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('id', 'title', 'content', 'homework', 'events', 'resources', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        """Enforce mutual exclusivity: only one of homework, events, or resources can be set."""
        homework = attrs.get('homework', [])
        events = attrs.get('events', [])
        resources = attrs.get('resources', [])

        # For updates, also consider existing values if not being updated
        if self.instance:
            if 'homework' not in attrs:
                homework = list(self.instance.homework.all())
            if 'events' not in attrs:
                events = list(self.instance.events.all())
            if 'resources' not in attrs:
                resources = list(self.instance.resources.all())

        linked_count = sum([
            len(homework) > 0 if homework else False,
            len(events) > 0 if events else False,
            len(resources) > 0 if resources else False,
        ])

        if linked_count > 1:
            raise ValidationError(
                'A note can only be linked to one type of entity (homework, event, or resource).'
            )

        # Enforce one-to-one: only allow one item per type
        if homework and len(homework) > 1:
            raise ValidationError(
                'A note can only be linked to one homework assignment.'
            )
        if events and len(events) > 1:
            raise ValidationError(
                'A note can only be linked to one event.'
            )
        if resources and len(resources) > 1:
            raise ValidationError(
                'A note can only be linked to one resource.'
            )

        return attrs

    def update(self, instance, validated_data):
        """Override to implement dual-write for legacy frontend compatibility."""
        instance = super().update(instance, validated_data)

        # Dual-write: sync content to linked entity's notes field
        if 'content' in validated_data:
            entity = instance.linked_entity
            if entity and hasattr(entity, 'notes'):
                entity.notes = instance.content
                entity.save(update_fields=['notes', 'updated_at'])

        return instance

    def should_delete_on_empty_content(self, instance, validated_data):
        """Check if Note should be deleted due to empty content with linked entities."""
        if 'content' not in validated_data:
            return False
        content = validated_data.get('content')
        content_is_empty = not content or content == {} or content == {'ops': [{'insert': '\n'}]}
        return content_is_empty and instance.has_linked_entity()


class NoteExtendedSerializer(NoteSerializer):
    """Includes link info on GET requests for backward compatibility."""
    linked_entity_type = serializers.ReadOnlyField()
    linked_entity_title = serializers.ReadOnlyField()
    course_color = serializers.ReadOnlyField()
    category_color = serializers.ReadOnlyField()

    class Meta(NoteSerializer.Meta):
        fields = NoteSerializer.Meta.fields + (
            'linked_entity_type', 'linked_entity_title', 'course_color', 'category_color'
        )


class NoteListSerializer(NoteExtendedSerializer):
    """Serializer for list endpoints - excludes content to reduce payload size."""

    class Meta(NoteExtendedSerializer.Meta):
        fields = tuple(f for f in NoteExtendedSerializer.Meta.fields if f != 'content')
