"""
UserSetting model.
"""

import logging

from django.conf import settings
from django.db import models

from helium.common import enums
from helium.common.models.base import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSetting(BaseModel):
    time_zone = models.CharField(default='America/Los_Angeles', max_length=255, choices=enums.TIME_ZONE_CHOICES)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='settings', on_delete=models.CASCADE)
