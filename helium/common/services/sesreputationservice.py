__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import base64
import json
import logging
import re
from functools import lru_cache

from django.contrib.auth import get_user_model
from django.db import IntegrityError

from helium.common.utils.httputils import urlopen_secure

from helium.common.models import (
    EmailReputationEvent,
    EMAIL_TYPE_CHOICES,
    EMAIL_TYPE_UNKNOWN,
    EVENT_TYPE_BOUNCE,
    EVENT_TYPE_COMPLAINT,
    BOUNCE_SUBTYPE_PERMANENT,
)
from helium.common.utils import metricutils
from helium.common.utils.commonutils import add_to_ses_suppression_list, redact_email

logger = logging.getLogger(__name__)

_SNS_CERT_URL_PATTERN = re.compile(r'^https://sns\.[a-z0-9-]+\.amazonaws\.com/')

_VALID_EMAIL_TYPES = {choice[0] for choice in EMAIL_TYPE_CHOICES}

#: Email types where a single complaint triggers immediate suppression.
_SUPPRESS_ON_FIRST_COMPLAINT = {
    'dormant_warning',
}

#: Email types that are purely informational and never trigger suppression regardless of count.
_NEVER_SUPPRESS_ON_COMPLAINT = {
    'verification',
    'registration',
    'password_reset',
}


@lru_cache(maxsize=16)
def _fetch_sns_cert(cert_url: str):
    from cryptography.x509 import load_pem_x509_certificate

    if not _SNS_CERT_URL_PATTERN.match(cert_url):
        raise ValueError(f"Untrusted SNS certificate URL: {cert_url}")

    with urlopen_secure(cert_url, timeout=10) as response:
        return load_pem_x509_certificate(response.read())


def verify_sns_message(message: dict) -> None:
    """
    Verify an SNS message signature.

    Raises :class:`ValueError` if the signature is invalid or the certificate URL
    is not hosted on ``sns.*.amazonaws.com`` (cert-substitution protection).

    :param message: The parsed SNS notification dict.
    :raises ValueError: On any verification failure.
    """
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    msg_type = message.get('Type', '')
    cert_url = message.get('SigningCertURL', '')
    raw_signature = message.get('Signature', '')

    cert = _fetch_sns_cert(cert_url)

    if msg_type == 'Notification':
        fields = ['Message', 'MessageId', 'Subject', 'Timestamp', 'TopicArn', 'Type']
    elif msg_type in ('SubscriptionConfirmation', 'UnsubscribeConfirmation'):
        fields = ['Message', 'MessageId', 'SubscribeURL', 'Timestamp', 'Token', 'TopicArn', 'Type']
    else:
        raise ValueError(f"Unknown SNS message type: {msg_type!r}")

    string_to_sign = ''.join(
        f'{field}\n{message[field]}\n'
        for field in fields
        if field in message
    )

    try:
        cert.public_key().verify(
            base64.b64decode(raw_signature),
            string_to_sign.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
    except InvalidSignature as exc:
        raise ValueError("SNS message signature verification failed") from exc


def process_ses_notification(message_json: str) -> None:
    """
    Parse an SES event notification (the inner ``Message`` field from an SNS payload)
    and record bounce/complaint events.

    :param message_json: The raw JSON string from ``SNS.Message``.
    """
    try:
        notification = json.loads(message_json)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Received unparseable SES notification payload")
        return

    notification_type = (
        notification.get('notificationType') or notification.get('eventType') or ''
    )
    mail = notification.get('mail', {})
    sns_message_id = mail.get('messageId', '')
    email_type = _extract_email_type(mail)

    if notification_type == 'Bounce':
        bounce = notification.get('bounce', {})
        bounce_type = bounce.get('bounceType', '').lower()
        bounce_subtype = bounce.get('bounceSubType', '').lower()

        for recipient in bounce.get('bouncedRecipients', []):
            email = recipient.get('emailAddress', '')
            if email:
                _record_bounce(email, email_type, bounce_type, bounce_subtype, sns_message_id)

    elif notification_type == 'Complaint':
        complaint = notification.get('complaint', {})
        feedback_type = (complaint.get('complaintFeedbackType') or 'other').lower()

        for recipient in complaint.get('complainedRecipients', []):
            email = recipient.get('emailAddress', '')
            if email:
                _record_complaint(email, email_type, feedback_type, sns_message_id)

    else:
        logger.debug(f"Ignoring SES notification type: {notification_type!r}")


def _extract_email_type(mail: dict) -> str:
    tags = mail.get('tags', {})
    values = tags.get('email_type', [])
    if values:
        candidate = values[0].lower()
        if candidate in _VALID_EMAIL_TYPES:
            return candidate
    return EMAIL_TYPE_UNKNOWN


def _record_bounce(
    email: str,
    email_type: str,
    bounce_type: str,
    bounce_subtype: str,
    sns_message_id: str,
) -> None:
    is_hard = bounce_type == BOUNCE_SUBTYPE_PERMANENT
    subtype = f'{bounce_type}_{bounce_subtype}' if bounce_subtype else bounce_type or None

    try:
        EmailReputationEvent.objects.create(
            user=_lookup_user(email),
            email=email,
            email_type=email_type,
            event_type=EVENT_TYPE_BOUNCE,
            event_subtype=subtype,
            sns_message_id=sns_message_id,
        )
    except IntegrityError:
        logger.debug(
            f"Duplicate bounce event for {redact_email(email)} "
            f"(sns_message_id={sns_message_id}); skipping"
        )
        return
    except Exception:
        logger.warning(
            f"Failed to record bounce event for {redact_email(email)} "
            f"(sns_message_id={sns_message_id})",
            exc_info=True,
        )
        return

    if is_hard:
        logger.info(f"Hard bounce for {redact_email(email)} ({email_type}); adding to suppression list")
        add_to_ses_suppression_list(email)
        metricutils.increment('ses.reputation.suppressed', extra_tags=[f'reason:hard_bounce', f'email_type:{email_type}'])
    else:
        metricutils.increment('ses.reputation.soft_bounce', extra_tags=[f'email_type:{email_type}'])


def _record_complaint(
    email: str,
    email_type: str,
    feedback_type: str,
    sns_message_id: str,
) -> None:
    try:
        EmailReputationEvent.objects.create(
            user=_lookup_user(email),
            email=email,
            email_type=email_type,
            event_type=EVENT_TYPE_COMPLAINT,
            event_subtype=feedback_type or None,
            sns_message_id=sns_message_id,
        )
    except IntegrityError:
        logger.debug(
            f"Duplicate complaint event for {redact_email(email)} "
            f"(sns_message_id={sns_message_id}); skipping"
        )
        return
    except Exception:
        logger.warning(
            f"Failed to record complaint event for {redact_email(email)} "
            f"(sns_message_id={sns_message_id})",
            exc_info=True,
        )
        return

    metricutils.increment('ses.reputation.complaint', extra_tags=[f'email_type:{email_type}', f'feedback:{feedback_type}'])

    if email_type in _NEVER_SUPPRESS_ON_COMPLAINT:
        logger.info(f"Complaint ({email_type}) for {redact_email(email)}; logged only, no suppression")
        return

    if email_type in _SUPPRESS_ON_FIRST_COMPLAINT:
        logger.info(f"Complaint ({email_type}) for {redact_email(email)}; suppressing immediately")
        add_to_ses_suppression_list(email, reason='COMPLAINT')
        metricutils.increment('ses.reputation.suppressed', extra_tags=[f'reason:complaint', f'email_type:{email_type}'])
        return

    from django.conf import settings
    threshold = getattr(settings, 'SES_COMPLAINT_SUPPRESS_THRESHOLD', 2)
    complaint_count = EmailReputationEvent.objects.filter(
        email__iexact=email, event_type=EVENT_TYPE_COMPLAINT
    ).count()
    if complaint_count >= threshold:
        logger.info(
            f"Complaint #{complaint_count} ({email_type}) for {redact_email(email)}; "
            f"threshold {threshold} reached, suppressing"
        )
        add_to_ses_suppression_list(email, reason='COMPLAINT')
        metricutils.increment('ses.reputation.suppressed', extra_tags=[f'reason:complaint_threshold', f'email_type:{email_type}'])


def _lookup_user(email: str):
    """Return the User matching this email, or None."""
    UserModel = get_user_model()
    return UserModel.objects.filter(email__iexact=email).first()
