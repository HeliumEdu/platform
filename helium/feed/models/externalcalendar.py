"""
ExternalCalendar model.
"""
import logging

from builtins import str
from django.conf import settings
from django.db import models

from helium.common import enums
from helium.planner.models.base import BasePlannerModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendar(BasePlannerModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    url = models.URLField(max_length=255)

    color = models.CharField(max_length=7, choices=enums.ALLOWED_COLORS, default='#4986e7')

    shown_on_calendar = models.BooleanField(default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='external_calendars')

    def __unicode__(self):
        return str('{} ({})'.format(self.title, self.get_user().get_username()))

    def get_user(self):
        return self.user
