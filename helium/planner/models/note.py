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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='notes',
        on_delete=models.CASCADE
    )

    objects = NoteManager()

    class Meta:
        ordering = ('-updated_at',)

    def __str__(self):
        return f'{self.title or "Untitled"} ({self.user.get_username()})'

    def get_user(self):
        return self.user
