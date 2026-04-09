__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.db import models


class UserClientActivity(models.Model):
    CLIENT_MOBILE_APP = 'mobile_app'
    CLIENT_WEB = 'web'
    CLIENT_CHOICES = [
        (CLIENT_MOBILE_APP, 'Mobile App'),
        (CLIENT_WEB, 'Web'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_activity',
    )

    date = models.DateField(db_index=True)

    client = models.CharField(max_length=20, choices=CLIENT_CHOICES)

    class Meta:
        app_label = 'helium_auth'
        unique_together = ('user', 'date', 'client')
        verbose_name_plural = 'User client activities'
