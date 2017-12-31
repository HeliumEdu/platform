import logging

from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.common import enums
from helium.common.models.base import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class ExternalCalendar(BaseModel):
    title = models.CharField(help_text='A display name.',
                             max_length=255, db_index=True)

    url = models.URLField(help_text='A public-facing URL to a valid ICAL feed.',
                          max_length=255)

    color = models.CharField(help_text='A hex color code to determine the color items will be shown on the calendar',
                             max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    shown_on_calendar = models.BooleanField(help_text='Whether or not items should be shown on the calendar.',
                                            default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='external_calendars')

    def __str__(self):
        return '{} ({})'.format(self.title, self.get_user().get_username())

    def get_user(self):
        return self.user
