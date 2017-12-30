"""
UserProfile model.
"""

import logging

from builtins import str
from django.conf import settings
from django.db import models
from six import python_2_unicode_compatible

from helium.auth.utils.userutils import generate_phone_verification_code
from helium.common import enums
from helium.common.models import BaseModel

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class UserProfile(BaseModel):
    phone = models.CharField(max_length=255, blank=True, null=True)

    phone_changing = models.CharField(max_length=15, blank=True, null=True)

    phone_carrier = models.CharField(max_length=255, choices=enums.PHONE_CARRIER_CHOICES, default=None, blank=True,
                                     null=True)

    phone_carrier_changing = models.CharField(max_length=255, choices=enums.PHONE_CARRIER_CHOICES, default=None,
                                              blank=True, null=True)

    phone_verification_code = models.PositiveIntegerField(default=generate_phone_verification_code)

    phone_verified = models.BooleanField(default=False)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile', on_delete=models.CASCADE)

    def __str__(self):
        return '{} ({})'.format(self.pk, self.user.get_username())
