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

    def _get_cached_m2m(self, attr_name):
        """Get M2M relation as list, using prefetch cache if available."""
        manager = getattr(self, attr_name)
        # Check if prefetch cache exists to avoid extra query
        if manager.all()._result_cache is not None:
            return list(manager.all())
        # Fallback: access without triggering full query if possible
        return list(manager.all())

    @property
    def linked_entity(self):
        """Returns the first linked entity or None.

        Uses prefetch cache when available to avoid N+1 queries.
        """
        hw_list = self._get_cached_m2m('homework')
        if hw_list:
            return hw_list[0]
        events_list = self._get_cached_m2m('events')
        if events_list:
            return events_list[0]
        resources_list = self._get_cached_m2m('resources')
        if resources_list:
            return resources_list[0]
        return None

    @property
    def linked_entity_type(self):
        """Returns string type of linked entity.

        Uses prefetch cache when available to avoid N+1 queries.
        """
        if self._get_cached_m2m('homework'):
            return 'homework'
        if self._get_cached_m2m('events'):
            return 'event'
        if self._get_cached_m2m('resources'):
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
        Uses prefetch cache when available (expects 'homework__course' prefetch).
        """
        hw_list = self._get_cached_m2m('homework')
        if hw_list:
            hw = hw_list[0]
            if hw.course:
                return hw.course.color
        return None

    @property
    def category_color(self):
        """Returns hex color from linked homework's category.

        Only applicable when linked entity is homework.
        Returns None for events/resources or if no homework linked.
        Uses prefetch cache when available (expects 'homework__category' prefetch).
        """
        hw_list = self._get_cached_m2m('homework')
        if hw_list:
            hw = hw_list[0]
            if hw.category:
                return hw.category.color
        return None

    def has_linked_entity(self):
        """Check if note has any linked entity.

        Uses prefetch cache when available to avoid N+1 queries.
        """
        return bool(
            self._get_cached_m2m('homework') or
            self._get_cached_m2m('events') or
            self._get_cached_m2m('resources')
        )
