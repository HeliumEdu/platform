__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import Homework, Category, Material, Course
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.tasks import recalculate_category_grade

logger = logging.getLogger(__name__)


class HomeworkSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['category'].queryset = Category.objects.for_user(self.context['request'].user.pk)
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)
            # ManyToMany fields need to have their `child_relation` queryset modified instead
            self.fields['materials'].child_relation.queryset = Material.objects.for_user(
                self.context['request'].user.pk)

    class Meta:
        model = Homework
        fields = (
            'id', 'title', 'all_day', 'show_end_time', 'start', 'end', 'priority', 'comments', 'notes',
            'current_grade', 'completed', 'category', 'materials', 'attachments', 'reminders', 'course',
            # Property fields (which should also be declared as read-only)
            'calendar_item_type',)
        read_only_fields = ('attachments', 'reminders', 'calendar_item_type',)

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
        old_category = self.instance.category if 'category' in validated_data and self.instance.category_id != \
                                                                                  validated_data['category'] else None

        instance = super().update(instance, validated_data)

        if old_category:
            recalculate_category_grade(old_category.pk)

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
                    title=f'Notes for: {instance.title}',
                    content=notes_content,
                    user=instance.course.course_group.user,
                )
                NoteLink.objects.create(note=note, homework=instance)
        elif link:
            # Notes cleared - delete the linked Note
            link.note.delete()


class HomeworkExtendedSerializer(HomeworkSerializer):
    attachments = AttachmentSerializer(many=True)

    reminders = ReminderSerializer(many=True)

    note = serializers.SerializerMethodField()

    class Meta(HomeworkSerializer.Meta):
        fields = HomeworkSerializer.Meta.fields + ('note',)

    def get_note(self, obj):
        """Return the linked Note's id if one exists."""
        link = obj.note_links.select_related('note').first()
        if link:
            return {'id': link.note.id, 'title': link.note.title}
        return None
