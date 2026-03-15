__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models import Note, NoteLink

logger = logging.getLogger(__name__)


class NoteLinkSerializer(serializers.ModelSerializer):
    linked_entity_type = serializers.ReadOnlyField()
    linked_entity_title = serializers.ReadOnlyField()
    linked_entity_color = serializers.ReadOnlyField()
    linked_entity_color_alt = serializers.ReadOnlyField()

    class Meta:
        model = NoteLink
        fields = ('id', 'note', 'homework', 'event', 'resource',
                  'linked_entity_type', 'linked_entity_title', 'linked_entity_color',
                  'linked_entity_color_alt')
        read_only_fields = ('linked_entity_type', 'linked_entity_title', 'linked_entity_color',
                            'linked_entity_color_alt')

    def validate(self, attrs):
        if not self.instance:
            note = attrs.get('note')
            if note and note.links.exists():
                raise ValidationError(
                    f'Note {note.pk} already has a link and cannot have more than one.'
                )

        return attrs


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('id', 'title', 'content', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def update(self, instance, validated_data):
        """Override to implement dual-write for legacy frontend compatibility."""
        instance = super().update(instance, validated_data)

        # Dual-write: sync content to linked entity's notes field
        if 'content' in validated_data:
            for link in instance.links.select_related('homework', 'event', 'resource').all():
                entity = link.linked_entity
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
        return content_is_empty and instance.links.exists()


class NoteExtendedSerializer(NoteSerializer):
    """Includes link info on GET requests.

    Note: Returns first link only. For v1, each Note has at most one link.
    Future tagging may change this to return all links.
    """
    link = serializers.SerializerMethodField()

    class Meta(NoteSerializer.Meta):
        fields = NoteSerializer.Meta.fields + ('link',)

    def get_link(self, obj):
        # Return first link (v1: one link per note max)
        link = obj.links.first()
        if link:
            return NoteLinkSerializer(link).data
        return None


class NoteListSerializer(NoteExtendedSerializer):
    """Serializer for list endpoints - excludes content to reduce payload size."""

    class Meta(NoteExtendedSerializer.Meta):
        fields = tuple(f for f in NoteExtendedSerializer.Meta.fields if f != 'content')
