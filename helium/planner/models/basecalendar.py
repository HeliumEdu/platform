from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models

from helium.common.models import BaseModel
from helium.common.utils import datetimeutils


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
        help_text='Should be stored in increments of 10.',
        default=50, validators=[MaxValueValidator(100)])

    url = models.URLField(max_length=3000, help_text='An optional URL that the calendar item references.',
                          blank=True, null=True)

    recurrence_rule = models.CharField(
        help_text='iCal RRULE string (e.g. `FREQ=WEEKLY;BYDAY=MO,WE,FR`) that repeats it from `start`, or null.',
        max_length=500, blank=True, null=True)

    exception_dates = models.JSONField(
        help_text='List of ISO-8601 datetimes of occurrences to skip (iCal EXDATE).',
        blank=True, null=True)

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

    def occurrences(self, not_before=None):
        """
        Lazily expand this repeating item into its ``(start, end)`` occurrences, in the user's time zone. See
        :func:`helium.common.utils.datetimeutils.expand_recurrence`.

        :param not_before: Aware datetime; occurrences starting before it are not yielded, or None.
        """
        return datetimeutils.expand_recurrence(self.recurrence_rule, self.start, self.end,
                                               ZoneInfo(self.get_user().settings.time_zone), all_day=self.all_day,
                                               exception_dates=self.exception_dates, not_before=not_before)
