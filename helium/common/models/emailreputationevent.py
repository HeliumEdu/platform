__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.contrib.auth import get_user_model
from django.db import models

EMAIL_TYPE_VERIFICATION = 'verification'
EMAIL_TYPE_REGISTRATION = 'registration'
EMAIL_TYPE_PASSWORD_RESET = 'password_reset'
EMAIL_TYPE_DORMANT_WARNING = 'dormant_warning'
EMAIL_TYPE_REMINDER = 'reminder'
EMAIL_TYPE_UNKNOWN = 'unknown'

EMAIL_TYPE_CHOICES = [
    (EMAIL_TYPE_VERIFICATION, 'Verification'),
    (EMAIL_TYPE_REGISTRATION, 'Registration'),
    (EMAIL_TYPE_PASSWORD_RESET, 'Password Reset'),
    (EMAIL_TYPE_DORMANT_WARNING, 'Dormant Warning'),
    (EMAIL_TYPE_REMINDER, 'Reminder'),
    (EMAIL_TYPE_UNKNOWN, 'Unknown'),
]

EVENT_TYPE_BOUNCE = 'bounce'
EVENT_TYPE_COMPLAINT = 'complaint'

EVENT_TYPE_CHOICES = [
    (EVENT_TYPE_BOUNCE, 'Bounce'),
    (EVENT_TYPE_COMPLAINT, 'Complaint'),
]

BOUNCE_SUBTYPE_PERMANENT = 'permanent'
BOUNCE_SUBTYPE_TRANSIENT = 'transient'
BOUNCE_SUBTYPE_UNDETERMINED = 'undetermined'

COMPLAINT_SUBTYPE_ABUSE = 'abuse'
COMPLAINT_SUBTYPE_AUTH_FAILURE = 'auth_failure'
COMPLAINT_SUBTYPE_FRAUD = 'fraud'
COMPLAINT_SUBTYPE_NOT_SPAM = 'not_spam'
COMPLAINT_SUBTYPE_OTHER = 'other'
COMPLAINT_SUBTYPE_VIRUS = 'virus'


class EmailReputationEvent(models.Model):
    """
    Append-only log of individual SES bounce and complaint events received via SNS webhook.

    The recipient email is never stored in plaintext. Only an HMAC-SHA256 hash is kept so
    records can be looked up without exposing PII in the database. The ``user`` FK provides
    the actionable link to an account when the recipient matched a registered user.
    """

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    #: FK to the user account, if the destination email matched one at event time.
    #: SET_NULL preserves reputation history even after account deletion.
    user = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='email_reputation_events',
    )

    #: HMAC-SHA256 of the normalised recipient email address (lowercased, stripped).
    email_hash = models.CharField(max_length=64, db_index=True)

    #: The category of email that triggered the event, carried via X-SES-MESSAGE-TAGS.
    email_type = models.CharField(max_length=50, choices=EMAIL_TYPE_CHOICES, default=EMAIL_TYPE_UNKNOWN)

    #: Top-level classification: bounce or complaint.
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)

    #: Finer-grained subtype (e.g. permanent/transient for bounces; abuse/fraud for complaints).
    event_subtype = models.CharField(max_length=50, null=True, blank=True)

    #: SNS MessageId — deduplicates redeliveries.
    sns_message_id = models.CharField(max_length=100, unique=True)

    class Meta:
        app_label = 'helium_common'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_hash', 'event_type']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} / {self.get_email_type_display()} ({self.created_at:%Y-%m-%d})'
