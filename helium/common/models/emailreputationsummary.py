__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.contrib.auth import get_user_model
from django.db import models

from helium.common.models.emailreputationevent import EVENT_TYPE_CHOICES


class EmailReputationSummary(models.Model):
    """
    Aggregated per-address reputation counters. One row per unique email hash.

    Updated atomically each time a new :class:`EmailReputationEvent` is recorded so
    Django Admin can surface actionable data without querying the full event log.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    #: FK to the matched user account (set when first matched; survives subsequent SET_NULL
    #: on the event rows if the user is later deleted, but also SET_NULL here).
    user = models.OneToOneField(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='email_reputation_summary',
    )

    #: HMAC-SHA256 of the normalised email — unique index enables O(1) lookups on send.
    email_hash = models.CharField(max_length=64, unique=True)

    hard_bounce_count = models.IntegerField(default=0)
    soft_bounce_count = models.IntegerField(default=0)
    complaint_count = models.IntegerField(default=0)

    last_event_at = models.DateTimeField(null=True, blank=True)
    last_event_type = models.CharField(max_length=20, null=True, blank=True, choices=EVENT_TYPE_CHOICES)

    class Meta:
        app_label = 'helium_common'
        ordering = ['-updated_at']
        verbose_name_plural = 'email reputation summaries'

    def __str__(self):
        user_label = self.user.email if self.user else self.email_hash[:12] + '…'
        return (
            f'{user_label} — '
            f'hard={self.hard_bounce_count} soft={self.soft_bounce_count} complaints={self.complaint_count}'
        )
