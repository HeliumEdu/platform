import logging

from django.conf import settings
from django.db import models

from helium.common import enums
from helium.common.models.base import BaseModel
from helium.feed.managers.externalcalendarmanager import ExternalCalendarManager

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Helium Edu"
__version__ = "1.4.56"

logger = logging.getLogger(__name__)


class ExternalCalendar(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    url = models.URLField(help_text='A public-facing URL to a valid ICAL feed.',
                          max_length=3000)

    color = models.CharField(
        help_text='A valid hex color code choice to determine the color items will be shown on the calendar',
        max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    shown_on_calendar = models.BooleanField(help_text='Whether or not items should be shown on the calendar.',
                                            default=True, db_index=True)

    last_index = models.DateTimeField(help_text='The last time this calendar was indexed to the cache.',
                                      blank=True, null=True, db_index=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='external_calendars', on_delete=models.CASCADE)

    objects = ExternalCalendarManager()

    class Meta:
        ordering = ('title',)

    def __str__(self):  # pragma: no cover
        return f'{self.title} ({self.get_user().get_username()})'

    def get_user(self):
        return self.user
