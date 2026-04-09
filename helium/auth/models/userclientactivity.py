__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.db import models


class UserClientActivity(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_activity',
    )

    date = models.DateField(db_index=True)

    class Meta:
        app_label = 'helium_auth'
        unique_together = ('user', 'date')
        verbose_name_plural = 'User client activities'
