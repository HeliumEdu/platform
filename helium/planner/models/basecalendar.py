from django.db import models
from six import python_2_unicode_compatible

from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


@python_2_unicode_compatible
class BaseCalendar(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    all_day = models.BooleanField(help_text='Whether or not it is an all day event.',
                                  default=False)

    show_end_time = models.BooleanField(help_text='Whether or not the end time should be shown on the calendar.',
                                        default=False)

    start = models.DateTimeField(help_text='An ISO-8601 date.')

    end = models.DateTimeField(help_text='An ISO-8601 date.')

    priority = models.PositiveIntegerField(help_text='A priority integer between 0 and 100.',
                                           default=50)

    url = models.URLField(max_length=3000, help_text='An optional URL that the calendar item references.',
                          blank=True, null=True)

    comments = models.TextField(help_text='An arbitrary string (which may contain HTML formatting).',
                                blank=True)

    class Meta:
        abstract = True
        ordering = ('start',)

    def __str__(self):  # pragma: no cover
        return '{} ({})'.format(self.title, self.get_user().get_username())

    @property
    def calendar_item_type(self):
        raise NotImplementedError
