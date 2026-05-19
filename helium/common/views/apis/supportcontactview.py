__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from helium.common.serializers.supportcontactserializer import SupportContactSerializer
from helium.common.services.jsmservice import JsmRequestException, create_jsm_request
from helium.common.throttles import SupportContactThrottle
from helium.common.utils import metricutils
from helium.common.utils.commonutils import redact_email
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
class SupportContactView(HeliumAPIView):
    """
    Accepts a public support contact form submission and creates a JSM service desk
    request on behalf of the submitter via the authenticated JSM Cloud REST API.
    """

    serializer_class = SupportContactSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [SupportContactThrottle]

    def _client_ip(self, request):
        """
        Resolve the submitter IP. Returns the first ``X-Forwarded-For`` hop when
        present, otherwise the direct peer address.
        """
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if forwarded:
            return forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    def post(self, request, *args, **kwargs):
        """
        Validate the submission and create a JSM service desk request on behalf
        of the submitter.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get('website'):
            logger.warning(
                f'support contact submission rejected (ip={self._client_ip(request)})'
            )
            metricutils.increment('action.support_contact.honeypot')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        if settings.DISABLE_EMAILS:
            logger.warning(
                f'Emails disabled. Discarding support contact from {redact_email(data["email"])}'
            )
            return Response({'ok': True}, status=status.HTTP_200_OK)

        try:
            create_jsm_request(
                subject=data['subject'],
                category=data['category'],
                email=data['email'],
                description=data['description'],
                attachments=data.get('attachment', []),
            )
        except JsmRequestException:
            return Response(
                {'detail': (
                    'We were unable to deliver your message. '
                    f'Please email {settings.ADMIN_EMAIL_ADDRESS} directly.'
                )},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'ok': True}, status=status.HTTP_200_OK)
