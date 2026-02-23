__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import json

from firebase_admin import messaging

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


def send_notifications(push_tokens, subject, message, reminder_data):
    multicast_message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=subject,
            body=message,
        ),
        data={"json_payload": json.dumps(reminder_data)},
        tokens=push_tokens
    )

    try:
        response = messaging.send_each_for_multicast(multicast_message)

        if response.success_count > 0:
            metricutils.increment('action.push.sent', value=response.success_count)

        if response.failure_count > 0:
            logger.warning(f"Failed to send {response.failure_count} push notifications")
            metricutils.increment('action.push.failed', value=response.failure_count)
    except Exception:
        logger.error("Failed to send push notifications", exc_info=True)
        metricutils.increment('action.push.failed', value=len(push_tokens))
        raise
