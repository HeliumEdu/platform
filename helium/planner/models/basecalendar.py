__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from helium.common.models import BaseModel


class BaseCalendar(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255)

    all_day = models.BooleanField(help_text='Whether it is an all day event.',
                                  default=False)

    show_end_time = models.BooleanField(help_text='Whether the end time should be shown on the calendar.',
                                        default=False)

    start = models.DateTimeField(
        help_text=(
            'ISO-8601 datetime with offset. Server normalizes to UTC and handles DST. '
            'Must be on-or-before `end`.'
        ),
        db_index=True)

    end = models.DateTimeField(
        help_text='ISO-8601 datetime with offset. Must be on-or-after `start`.',
        db_index=True)

    priority = models.PositiveIntegerField(
        help_text=(
            'Should be stored in increments of 10. '
            'Suggested: `50` routine, `80` exam, `90` final.'
        ),
        default=50, validators=[MaxValueValidator(100)])

    url = models.URLField(max_length=3000, help_text='An optional URL that the calendar item references.',
                          blank=True, null=True)

    comments = models.TextField(help_text='An arbitrary string (which may contain HTML formatting).',
                                blank=True, default='')

    class Meta:
        abstract = True
        ordering = ('start', 'title')

    def clean(self):
        super().clean()
        if self.start and self.end and self.start > self.end:
            raise ValidationError("The 'start' must be before the 'end'")

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    @property
    def calendar_item_type(self) -> int:
        raise NotImplementedError
