__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.common.utils.validators import validate_hex_color
from helium.planner.models import Event
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer

logger = logging.getLogger(__name__)


class EventSerializer(serializers.ModelSerializer):
    color = serializers.CharField(max_length=7, validators=[validate_hex_color], read_only=True, required=False)
    location = serializers.CharField(read_only=True, required=False, allow_null=True)

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'url', 'comments', 'notes',
            'owner_id',
            'color', 'location', 'attachments', 'reminders', 'user',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'user', 'calendar_item_type',)

    def validate(self, attrs):
        start = attrs.get('start', None)
        if not start and self.instance:
            start = self.instance.start
        end = attrs.get('end', None)
        if not end and self.instance:
            end = self.instance.end

        if start and end and start > end:
            raise serializers.ValidationError("The 'start' must be before the 'end'")

        return attrs

    def create(self, validated_data):
        instance = super().create(validated_data)

        # Dual-write: sync inline notes to linked Note entity
        if 'notes' in validated_data:
            self._sync_notes_to_note_entity(instance, validated_data['notes'])

        return instance

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        # Dual-write: sync inline notes to linked Note entity
        if 'notes' in validated_data:
            self._sync_notes_to_note_entity(instance, validated_data['notes'])

        return instance

    def _sync_notes_to_note_entity(self, instance, notes_content):
        """Sync inline notes field to the linked Note entity (dual-write)."""
        from helium.planner.models import Note

        note = instance.notes_set.first()

        if notes_content and notes_content != {}:
            if note:
                # Update existing Note
                note.content = notes_content
                note.save(update_fields=['content', 'updated_at'])
            else:
                # Create new Note and link
                note = Note.objects.create(
                    title='',
                    content=notes_content,
                    user=instance.user,
                    example_schedule=instance.example_schedule,
                )
                note.events.add(instance)
        elif note:
            # Notes cleared - delete the linked Note
            note.delete()


class EventExtendedSerializer(EventSerializer):
    attachments = AttachmentSerializer(many=True)

    reminders = ReminderSerializer(many=True)

    note = serializers.SerializerMethodField()

    class Meta(EventSerializer.Meta):
        fields = EventSerializer.Meta.fields + ('note',)

    def get_note(self, obj):
        """Return the linked Note's id if one exists."""
        note = obj.notes_set.first()
        if note:
            return {'id': note.id, 'title': note.title}
        return None
