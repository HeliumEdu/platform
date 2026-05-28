__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.common.utils.validators import validate_quill_delta
from helium.planner.models import Event, Homework, Material, Note


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = ('id', 'title', 'content', 'homework', 'events', 'resources', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['homework'].child_relation.queryset = Homework.objects.for_user(
                self.context['request'].user.pk)
            self.fields['events'].child_relation.queryset = Event.objects.for_user(
                self.context['request'].user.pk)
            self.fields['resources'].child_relation.queryset = Material.objects.for_user(
                self.context['request'].user.pk)

    def to_internal_value(self, data):
        """
        Accept `materials` as a permanent key-based alias for `resources` on input only. If both
        are present in the same payload the input is invalid. Output always emits `resources`.
        """
        if isinstance(data, dict) and 'materials' in data:
            if 'resources' in data:
                raise ValidationError(
                    {'resources': ["Provide either 'resources' or 'materials', not both."]})
            data = {k: v for k, v in data.items() if k != 'materials'} | {'resources': data['materials']}
        return super().to_internal_value(data)

    def validate_content(self, value):
        validate_quill_delta(value)
        return value

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

        if sum([bool(homework), bool(events), bool(resources)]) > 1:
            raise ValidationError(
                'A note can only be linked to one type of entity (homework, event, or resource).'
            )

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

        # Enforce one-to-one from entity side: entity can only have one linked note
        exclude_pk = self.instance.pk if self.instance else None
        if homework:
            existing = Note.objects.filter(homework__in=homework)
            if exclude_pk:
                existing = existing.exclude(pk=exclude_pk)
            if existing.exists():
                raise ValidationError(
                    'This homework assignment already has a linked note.'
                )
        if events:
            existing = Note.objects.filter(events__in=events)
            if exclude_pk:
                existing = existing.exclude(pk=exclude_pk)
            if existing.exists():
                raise ValidationError(
                    'This event already has a linked note.'
                )
        if resources:
            existing = Note.objects.filter(resources__in=resources)
            if exclude_pk:
                existing = existing.exclude(pk=exclude_pk)
            if existing.exists():
                raise ValidationError(
                    'This resource already has a linked note.'
                )

        return attrs

    def should_delete_on_empty_content(self, instance, validated_data):
        """Check if Note should be deleted due to empty content with linked entities."""
        if 'content' not in validated_data:
            return False
        content = validated_data.get('content')
        content_is_empty = not content or content == {} or content == {'ops': [{'insert': '\n'}]}
        return content_is_empty and instance.has_linked_entity()


class NoteExtendedSerializer(NoteSerializer):
    linked_entity_type = serializers.ReadOnlyField()
    linked_entity_title = serializers.ReadOnlyField()
    linked_entity_due = serializers.ReadOnlyField()
    linked_entity_completed = serializers.ReadOnlyField()
    course_color = serializers.ReadOnlyField()
    category_color = serializers.ReadOnlyField()

    class Meta(NoteSerializer.Meta):
        fields = NoteSerializer.Meta.fields + (
            'linked_entity_type', 'linked_entity_title', 'linked_entity_due', 'linked_entity_completed',
            'course_color', 'category_color'
        )


class NoteListSerializer(NoteExtendedSerializer):
    """Compact note representation used in list responses; the full `content` field is omitted to keep payloads small."""

    class Meta(NoteExtendedSerializer.Meta):
        fields = tuple(f for f in NoteExtendedSerializer.Meta.fields if f != 'content')
