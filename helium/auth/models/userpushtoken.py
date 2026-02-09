__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.db import models

from helium.common.models import BaseModel

logger = logging.getLogger(__name__)


class UserPushToken(BaseModel):
    device_id = models.CharField(max_length=100,
                                 help_text='The unique identifier for the device linked to this token.')

    token = models.TextField(help_text='The token used for push notifications.')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='push_tokens', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'User push tokens'

    def __str__(self):  # pragma: no cover
        return f'{self.pk} ({self.user.get_username()})'

    def get_user(self):
        return self.user
