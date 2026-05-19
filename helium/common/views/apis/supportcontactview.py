__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from helium.common.serializers.supportcontactserializer import SupportContactSerializer
from helium.common.throttles import SupportContactThrottle
from helium.common.utils import metricutils
from helium.common.utils.commonutils import (
    EmailSuppressedException,
    redact_email,
    send_support_contact_email,
)
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class SupportContactView(HeliumAPIView):
    """
    Accepts a public support contact form submission and relays it via SES to the
    JSM email channel, where it lands as a new ticket. Unauthenticated by design;
    a per-IP throttle and a honeypot field provide light spam control.
    """

    serializer_class = SupportContactSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SupportContactThrottle]

    def post(self, request, *args, **kwargs):
        """
        Validate the submission, drop honeypot hits silently, and relay the
        message to the JSM email channel.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Unused, catches honeypot
        if data.get('website'):
            logger.info('Support contact submission discarded')
            metricutils.increment('action.support_contact.honeypot')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        if settings.DISABLE_EMAILS:
            logger.warning(
                f'Emails disabled. Discarding support contact from {redact_email(data["email"])}'
            )
            return Response({'ok': True}, status=status.HTTP_200_OK)

        try:
            send_support_contact_email(
                subject=data['subject'],
                category=data['category'],
                email=data['email'],
                description=data['description'],
                attachments=data.get('attachment', []),
            )
        except EmailSuppressedException:
            return Response(
                {'detail': (
                    'We were unable to deliver your message. '
                    f'Please email {settings.ADMIN_EMAIL_ADDRESS} directly.'
                )},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'ok': True}, status=status.HTTP_200_OK)
