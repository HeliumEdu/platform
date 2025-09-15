__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from django.conf import settings
from django.db import models

from helium.auth.utils.userutils import generate_phone_verification_code
from helium.common.models import BaseModel

logger = logging.getLogger(__name__)


class UserProfile(BaseModel):
    phone = models.CharField(help_text='A valid phone number.',
                             max_length=50, blank=True, null=True)

    phone_changing = models.CharField(max_length=50, blank=True, null=True)

    phone_verification_code = models.PositiveIntegerField(
        help_text='The code sent to `phone` when registering or changing a phone number.',
        default=generate_phone_verification_code)

    phone_verified = models.BooleanField(default=False)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name='profile', on_delete=models.CASCADE)

    def __str__(self):  # pragma: no cover
        return f'{self.pk} ({self.user.get_username()})'

    def get_user(self):
        return self.user
