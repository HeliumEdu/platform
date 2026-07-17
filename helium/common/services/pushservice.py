__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import json

from firebase_admin import messaging

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


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
            collapse_key=tag,
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
            logger.warning(f"Failed to send {response.failure_count} push notifications")
            metricutils.increment('action.push.failed', value=response.failure_count)

        return [
            push_tokens[i]
            for i, r in enumerate(response.responses)
            if not r.success and isinstance(r.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError))
        ]
    except Exception:
        logger.error("Failed to send push notifications", exc_info=True)
        metricutils.increment('action.push.failed', value=len(push_tokens))
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
            logger.warning(f"Failed to send {response.failure_count} dismiss pushes")

        return [
            push_tokens[i]
            for i, r in enumerate(response.responses)
            if not r.success and isinstance(r.exception, (messaging.UnregisteredError, messaging.SenderIdMismatchError))
        ]
    except Exception:
        logger.error("Failed to send dismiss pushes", exc_info=True)
        raise
