__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import Material, MaterialGroup, Course

logger = logging.getLogger(__name__)


class MaterialSerializer(serializers.ModelSerializer):
    note = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['material_group'].queryset = MaterialGroup.objects.for_user(self.context['request'].user.pk)
            # ManyToMany fields need to have their `child_relation` queryset modified instead
            self.fields['courses'].child_relation.queryset = Course.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Material
        fields = (
            'id', 'title', 'status', 'condition', 'website', 'price', 'details', 'notes', 'material_group',
            'courses', 'note')
        read_only_fields = ('note',)

    def get_note(self, obj):
        """Return the linked Note's id if one exists."""
        link = obj.note_links.first()
        if link:
            return {'id': link.note.id, 'title': link.note.title}
        return None

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
        from helium.planner.models import Note, NoteLink

        link = instance.note_links.select_related('note').first()

        if notes_content and notes_content != {}:
            if link:
                # Update existing Note
                link.note.content = notes_content
                link.note.save(update_fields=['content', 'updated_at'])
            else:
                # Create new Note and link
                note = Note.objects.create(
                    title=instance.title,
                    content=notes_content,
                    user=instance.material_group.user,
                )
                NoteLink.objects.create(note=note, resource=instance)
        elif link:
            # Notes cleared - delete the linked Note
            link.note.delete()
