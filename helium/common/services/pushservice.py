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

    multicast_message = messaging.MulticastMessage(
        data={"json_payload": json.dumps(payload_data)},
        android=messaging.AndroidConfig(
            notification=messaging.AndroidNotification(
                title=subject,
                body=message,
            ),
        ),
        apns=messaging.APNSConfig(
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
