__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"

import logging

import firebase_admin
from firebase_admin import messaging

logger = logging.getLogger(__name__)


def send_push(push_tokens, subject, message):
    message = messaging.MulticastMessage(
        notification=messaging.Notification(
            title=subject,
            body=message,
        ),
        tokens=push_tokens
    )

    messaging.send_each_for_multicast(message)
