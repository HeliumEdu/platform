import logging
import json

from firebase_admin import exceptions as firebase_exceptions
from firebase_admin import messaging

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)

#: FCM's own types say more than the API codes they extend (an UnregisteredError is a NOT_FOUND).
#: The first two mean the token is dead, which is routine churn rather than a delivery problem.
_FAILURE_REASONS = (
    (messaging.UnregisteredError, 'unregistered'),
    (messaging.SenderIdMismatchError, 'sender_id_mismatch'),
    (messaging.ThirdPartyAuthError, 'third_party_auth'),
    (messaging.QuotaExceededError, 'quota_exceeded'),
)

_PERMANENTLY_INVALID = (messaging.UnregisteredError, messaging.SenderIdMismatchError)

#: A malformed token and a rejected message both come back as HTTP 400, so only FCM's wording
#: separates them. Retiring on the message-level fault would end push on every device at once.
_INVALID_TOKEN_MARKERS = ('registration token', 'registration_token')

#: A retired token is expected lifecycle rather than a delivery problem: it is purged automatically
#: and counted as `action.push.token.purged`, so it neither alerts nor counts as a failure.
_ROUTINE_REASONS = ('unregistered',)


def _failure_reason(exception):
    """Prefer FCM's specific error types, else the Google API error code the SDK attaches
    (https://cloud.google.com/apis/design/errors#handling_errors)."""
    for error_type, reason in _FAILURE_REASONS:
        if isinstance(exception, error_type):
            return reason

    code = getattr(exception, 'code', None)

    return str(code).lower() if code else 'unknown'


def _count_failures_by_reason(responses):
    counts = {}

    for response in responses:
        if response.success:
            continue

        reason = _failure_reason(response.exception)
        counts[reason] = counts.get(reason, 0) + 1

    return counts


def _failure_details(responses):
    """FCM's own wording for each meaningful failure, which is the only thing that separates a
    token it rejects from a message it rejects."""
    details = {}

    for response in responses:
        if response.success or _failure_reason(response.exception) in _ROUTINE_REASONS:
            continue

        details.setdefault(_failure_reason(response.exception), str(response.exception))

    return details


def _record_send_failures(response, operation):
    """Count every failed send that carries meaning, leaving out routine token retirement.

    :return: All failures keyed by reason, and the subset worth surfacing.
    """
    reason_counts = _count_failures_by_reason(response.responses) or {'unknown': response.failure_count}
    meaningful = {reason: count for reason, count in reason_counts.items() if reason not in _ROUTINE_REASONS}

    for reason, count in meaningful.items():
        metricutils.increment('action.push.failed', value=count,
                              extra_tags=[f'reason:{reason}', f'operation:{operation}'])

    return reason_counts, meaningful, _failure_details(response.responses)


def _is_permanently_invalid(exception):
    if isinstance(exception, _PERMANENTLY_INVALID):
        return True

    if isinstance(exception, firebase_exceptions.InvalidArgumentError):
        return any(marker in str(exception).lower() for marker in _INVALID_TOKEN_MARKERS)

    return False


def _invalid_tokens(push_tokens, responses):
    return [push_tokens[i] for i, response in enumerate(responses)
            if not response.success and _is_permanently_invalid(response.exception)]


def send_notifications(push_tokens, subject, message, reminder_data):
    """Send push notifications and return a list of token strings that are permanently invalid."""
    # Merge the computed notification title/body into json_payload so web clients
    # (which receive data-only messages with no notification field) can display them.
    payload_data = {**reminder_data, 'notification_title': subject, 'notification_body': message}

    # Stable per-reminder tag so a later dismiss can cancel this exact notification
    # on every device.
    tag = f"reminder_{reminder_data['id']}"

    multicast_message = messaging.MulticastMessage(
        data={"json_payload": json.dumps(payload_data)},
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                title=subject,
                body=message,
                tag=tag,
            ),
        ),
        apns=messaging.APNSConfig(
            headers={'apns-collapse-id': tag},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(
                    alert=messaging.ApsAlert(
                        title=subject,
                        body=message,
                    ),
                    sound='default',
                ),
            ),
        ),
        tokens=push_tokens
    )

    try:
        response = messaging.send_each_for_multicast(multicast_message)

        if response.success_count > 0:
            metricutils.increment('action.push.sent', value=response.success_count)
            metricutils.increment('action.reminder.sent', value=response.success_count, extra_tags=['channel:push'])

        if response.failure_count > 0:
            reason_counts, meaningful, details = _record_send_failures(response, 'notification')
            log = logger.warning if meaningful else logger.info
            log(f"Failed to send {response.failure_count} push notifications: {reason_counts}"
                + (f" {details}" if details else ""))

        return _invalid_tokens(push_tokens, response.responses)
    except Exception:
        logger.error("Failed to send push notifications", exc_info=True)
        metricutils.increment('action.push.failed', value=len(push_tokens),
                              extra_tags=['reason:request_failed', 'operation:notification'])
        raise


def send_dismiss(push_tokens, reminder_id):
    """Send a silent, data-only push telling clients to clear a dismissed
    reminder's notification from their tray. Returns permanently-invalid tokens."""
    multicast_message = messaging.MulticastMessage(
        data={"action": "dismiss", "reminder_id": str(reminder_id)},
        android=messaging.AndroidConfig(priority='high'),
        apns=messaging.APNSConfig(
            headers={'apns-priority': '5', 'apns-push-type': 'background'},
            payload=messaging.APNSPayload(
                aps=messaging.Aps(content_available=True),
            ),
        ),
        tokens=push_tokens,
    )

    try:
        response = messaging.send_each_for_multicast(multicast_message)

        if response.failure_count > 0:
            reason_counts, meaningful, details = _record_send_failures(response, 'dismiss')
            log = logger.warning if meaningful else logger.info
            log(f"Failed to send {response.failure_count} dismiss pushes: {reason_counts}"
                + (f" {details}" if details else ""))

        return _invalid_tokens(push_tokens, response.responses)
    except Exception:
        logger.error("Failed to send dismiss pushes", exc_info=True)
        metricutils.increment('action.push.failed', value=len(push_tokens),
                              extra_tags=['reason:request_failed', 'operation:dismiss'])
        raise
