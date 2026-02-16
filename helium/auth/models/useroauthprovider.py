__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.db import models


class UserOAuthProvider(models.Model):
    """
    Tracks which OAuth providers (Google, Apple, etc.) a user has linked to their account.
    Allows users to have multiple authentication methods and switch between providers.
    """
    PROVIDER_GOOGLE = 'google'
    PROVIDER_APPLE = 'apple'

    PROVIDER_CHOICES = [
        (PROVIDER_GOOGLE, 'Google'),
        (PROVIDER_APPLE, 'Apple'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='oauth_providers',
        help_text='The user this OAuth provider is linked to'
    )

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        help_text='The OAuth provider (Google, Apple, etc.)'
    )

    provider_user_id = models.CharField(
        max_length=255,
        help_text='The unique user ID from the OAuth provider (Firebase UID)'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When this provider was first linked to the account'
    )

    last_used_at = models.DateTimeField(
        auto_now=True,
        help_text='When this provider was last used to sign in'
    )

    class Meta:
        unique_together = [
            ('user', 'provider'),  # One provider per user
            ('provider', 'provider_user_id'),  # One Firebase UID per provider
        ]
        ordering = ['-created_at']
        verbose_name = 'OAuth Provider'
        verbose_name_plural = 'OAuth Providers'

    def __str__(self):
        return f"{self.user.username} - {self.get_provider_display()}"
