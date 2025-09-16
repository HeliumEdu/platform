__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.30"

import logging

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel

logger = logging.getLogger(__name__)


class UserMobileToken(BaseModel):
    device_id = models.CharField(max_length=100,
                                 help_text='The unique identifier for the device that owns this token.')

    token = models.TextField(help_text='The mobile token used for push notifications.')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='mobile_tokens', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'User mobile tokens'

    def __str__(self):  # pragma: no cover
        return f'{self.pk} ({self.user.get_username()})'

    def get_user(self):
        return self.user
