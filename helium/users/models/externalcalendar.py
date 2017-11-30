"""
ExternalCalendar model.
"""
import logging

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel
from helium.common.utils.commonutils import generate_random_color

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendar(BaseModel):
    title = models.CharField(max_length=255, db_index=True, default='')

    url = models.URLField(max_length=255)

    color = models.CharField(max_length=7, default=generate_random_color)

    shown_on_calendar = models.BooleanField(default=True)

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='external_calendars')
