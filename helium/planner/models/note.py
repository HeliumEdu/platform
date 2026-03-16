__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel
from helium.planner.managers.notemanager import NoteManager


class Note(BaseModel):
    """A rich-text note owned by a user, optionally linked to entities."""

    title = models.CharField(
        help_text='Display title for the note.',
        max_length=255,
        blank=True,
        db_index=True
    )

    content = models.JSONField(
        help_text='Rich text content in Quill Delta format.',
        blank=True,
        null=True
    )

    example_schedule = models.BooleanField(
        help_text='Whether it is part of the example schedule.',
        default=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='notes',
        on_delete=models.CASCADE
    )

    homework = models.ManyToManyField(
        'Homework',
        related_name='notes_set',
        blank=True,
        help_text='Linked homework assignments.'
    )

    events = models.ManyToManyField(
        'Event',
        related_name='notes_set',
        blank=True,
        help_text='Linked events.'
    )

    resources = models.ManyToManyField(
        'Material',
        related_name='notes_set',
        blank=True,
        help_text='Linked resources (Material model).'
    )

    objects = NoteManager()

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.title or "Untitled"} ({self.user.get_username()})'

    def get_user(self):
        return self.user

    @property
    def linked_entity(self):
        """Returns the first linked entity or None."""
        hw = self.homework.first()
        if hw:
            return hw
        event = self.events.first()
        if event:
            return event
        resource = self.resources.first()
        if resource:
            return resource
        return None

    @property
    def linked_entity_type(self):
        """Returns string type of linked entity."""
        if self.homework.exists():
            return 'homework'
        if self.events.exists():
            return 'event'
        if self.resources.exists():
            return 'resource'
        return ''

    @property
    def linked_entity_title(self):
        """Returns title of linked entity."""
        entity = self.linked_entity
        return entity.title if entity else ''

    @property
    def course_color(self):
        """Returns hex color from linked homework's course.

        Only applicable when linked entity is homework.
        Returns None for events/resources or if no homework linked.
        """
        hw = self.homework.select_related('course').first()
        if hw and hw.course:
            return hw.course.color
        return None

    @property
    def category_color(self):
        """Returns hex color from linked homework's category.

        Only applicable when linked entity is homework.
        Returns None for events/resources or if no homework linked.
        """
        hw = self.homework.select_related('category').first()
        if hw and hw.category:
            return hw.category.color
        return None

    def has_linked_entity(self):
        """Check if note has any linked entity."""
        return self.homework.exists() or self.events.exists() or self.resources.exists()
