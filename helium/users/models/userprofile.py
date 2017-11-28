"""
UserSetting model.
"""

import logging

from django.db import models

from helium.common import enums
from helium.common.models.base import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    first_name = models.CharField(max_length=30, blank=True, null=True)

    last_name = models.CharField(max_length=30, blank=True, null=True)

    address_1 = models.CharField(max_length=255, blank=True, null=True)

    address_2 = models.CharField(max_length=255, blank=True, null=True)

    city = models.CharField(max_length=255, blank=True, null=True)

    state = models.CharField(choices=enums.STATE_CHOICES, max_length=2, blank=True, null=True)

    postal_code = models.CharField(max_length=255, blank=True, null=True)

    country = models.CharField(max_length=255, blank=True, null=True, default='United States')

    phone = models.CharField(max_length=255, blank=True, null=True)

    user = models.OneToOneField('User', related_name='profile', on_delete=models.CASCADE)
