__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import models
from django.db.models import Q

from helium.common.models import BaseModel


class NoteLink(BaseModel):
    """Links a Note to exactly one entity (Homework, Event, or Resource).

    Uses ForeignKey (not OneToOne) to match existing patterns and allow
    future flexibility for tagging/multi-entity associations.
    """

    note = models.ForeignKey(
        'Note',
        related_name='links',
        on_delete=models.CASCADE,
        help_text='The note being linked.'
    )

    homework = models.ForeignKey(
        'Homework',
        related_name='note_links',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text='Linked homework assignment.'
    )

    event = models.ForeignKey(
        'Event',
        related_name='note_links',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text='Linked event.'
    )

    resource = models.ForeignKey(
        'Material',
        related_name='note_links',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        help_text='Linked resource (Material model).'
    )

    class Meta:
        constraints = [
            # Exactly one entity must be linked per NoteLink row
            models.CheckConstraint(
                check=(
                    Q(homework__isnull=False, event__isnull=True, resource__isnull=True) |
                    Q(homework__isnull=True, event__isnull=False, resource__isnull=True) |
                    Q(homework__isnull=True, event__isnull=True, resource__isnull=False)
                ),
                name='notelink_exactly_one_entity'
            )
        ]

    def __str__(self):
        if self.homework:
            return f'Link: Note {self.note_id} -> Homework {self.homework_id}'
        if self.event:
            return f'Link: Note {self.note_id} -> Event {self.event_id}'
        if self.resource:
            return f'Link: Note {self.note_id} -> Resource {self.resource_id}'
        return f'Link: Note {self.note_id} (unlinked)'

    def get_user(self):
        return self.note.get_user()

    @property
    def linked_entity(self):
        """Returns the linked entity or None."""
        return self.homework or self.event or self.resource

    @property
    def linked_entity_type(self):
        """Returns string type of linked entity."""
        if self.homework:
            return 'homework'
        if self.event:
            return 'event'
        if self.resource:
            return 'resource'
        return ''

    @property
    def linked_entity_title(self):
        """Returns title of linked entity."""
        entity = self.linked_entity
        return entity.title if entity else ''

    @property
    def linked_entity_color(self):
        """Returns hex color of linked entity for frontend display.

        - Homework: color from homework.course.color
        - Event: no color (returns None)
        - Resource: no color (returns None)
        """
        if self.homework and self.homework.course:
            return self.homework.course.color
        return None
