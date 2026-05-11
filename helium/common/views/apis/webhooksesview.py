__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import logging
import urllib.request

from django.conf import settings
from django.core.cache import cache
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.common.services.sesreputationservice import verify_sns_message

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class WebhookSESView(APIView):
    """
    Receives SES bounce and complaint event notifications from AWS SNS.

    Accepts two SNS message types:

    - ``SubscriptionConfirmation`` — auto-confirms the SNS subscription by fetching
      the provided ``SubscribeURL``.
    - ``Notification`` — dispatches the SES event payload to a Celery task for
      async processing.

    All requests are signature-verified against the SNS signing certificate before
    any action is taken.
    """

    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("SNS webhook received non-JSON body")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            verify_sns_message(body)
        except Exception:
            logger.warning("SNS message signature verification failed", exc_info=True)
            return Response(status=status.HTTP_403_FORBIDDEN)

        expected_topic_arn = getattr(settings, 'SES_SNS_TOPIC_ARN', '')
        if expected_topic_arn and body.get('TopicArn') != expected_topic_arn:
            logger.warning(
                f"SNS message TopicArn {body.get('TopicArn')!r} does not match expected {expected_topic_arn!r}"
            )
            return Response(status=status.HTTP_403_FORBIDDEN)

        msg_type = body.get('Type', '')

        if msg_type == 'SubscriptionConfirmation':
            return self._handle_subscription_confirmation(body)

        if msg_type == 'Notification':
            return self._handle_notification(body)

        logger.debug(f"Ignoring SNS message type: {msg_type!r}")
        return Response(status=status.HTTP_200_OK)

    def _handle_subscription_confirmation(self, body: dict) -> Response:
        subscribe_url = body.get('SubscribeURL', '')
        if not subscribe_url.startswith('https://'):
            logger.warning(f"Refusing to confirm SNS subscription via non-HTTPS URL: {subscribe_url!r}")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            urllib.request.urlopen(subscribe_url, timeout=10)
            logger.info("SNS subscription confirmed successfully")
        except Exception:
            logger.error("Failed to confirm SNS subscription", exc_info=True)
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)

    def _handle_notification(self, body: dict) -> Response:
        from helium.common.tasks import process_ses_event
        from helium.common.utils import taskutils

        message_id = body.get('MessageId', '')
        if message_id:
            cache_key = f'sns:processed:{message_id}'
            if cache.add(cache_key, 1, timeout=86400) is False:
                logger.debug(f"Skipping already-processed SNS message: {message_id}")
                return Response(status=status.HTTP_200_OK)

        message_json = body.get('Message', '')
        if message_json:
            taskutils.safe_delay(process_ses_event, message_json)

        return Response(status=status.HTTP_200_OK)
