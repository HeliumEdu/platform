__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.14.7"

import logging

from firebase_admin import messaging

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


def send_notifications(push_tokens, subject, message):
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=subject,
            body=message,
        ),
        tokens=push_tokens
    )

    messaging.send_each_for_multicast(message)

    metricutils.increment('action.push.sent', value=len(push_tokens))
