__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
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
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='email_reputation_events',
    )

    email = models.EmailField(db_index=True)

    email_type = models.CharField(max_length=50, choices=EMAIL_TYPE_CHOICES, default=EMAIL_TYPE_UNKNOWN)

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)

    event_subtype = models.CharField(max_length=50, null=True, blank=True)

    sns_message_id = models.CharField(max_length=100, unique=True)

    class Meta:
        app_label = 'helium_common'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'event_type']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} / {self.get_email_type_display()} ({self.created_at:%Y-%m-%d})'
