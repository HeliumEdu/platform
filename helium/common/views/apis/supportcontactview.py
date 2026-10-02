import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from helium.common.serializers.supportcontactserializer import SupportContactSerializer
from helium.common.services.jsmservice import (
    JsmAttachmentException,
    JsmRequestException,
    create_jsm_request,
    create_quarantined_jsm_request,
)
from helium.common.throttles import SupportContactThrottle
from helium.common.utils import metricutils, spamutils
from helium.common.utils.commonutils import clear_ses_suppression_if_exists, redact_email
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

    def post(self, request, *args, **kwargs):
        """
        Validate the submission and create a JSM service desk request on behalf
        of the submitter.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data.get('website'):
            logger.info(
                f'support contact submission rejected (ip={SupportContactThrottle().get_ident(request)})'
            )
            metricutils.increment('action.support_contact.honeypot')
            return Response({'ok': True}, status=status.HTTP_200_OK)

        spam_signals = spamutils.detect_solicitation(data['subject'], data['description'])
        if spam_signals:
            logger.info(
                f'support contact from {redact_email(data["email"])} flagged as suspected spam '
                f'(signals={",".join(spam_signals)})'
            )
            metricutils.increment('action.support_contact.suspected_spam')

        if settings.DISABLE_EMAILS:
            logger.warning(
                f'Emails disabled. Discarding support contact from {redact_email(data["email"])}'
            )
            return Response({'ok': True}, status=status.HTTP_200_OK)

        clear_ses_suppression_if_exists(data['email'])

        fields = {
            'subject': data['subject'],
            'category': data['category'],
            'email': data['email'],
            'description': data['description'],
            'attachments': data.get('attachment', []),
        }

        try:
            if spam_signals:
                self._quarantine(fields, spam_signals)
            else:
                create_jsm_request(**fields)
        except JsmRequestException:
            return Response(
                {'detail': (
                    'We were unable to deliver your message. '
                    f'Please email {settings.ADMIN_EMAIL_ADDRESS} directly.'
                )},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({'ok': True}, status=status.HTTP_200_OK)

    @staticmethod
    def _quarantine(fields, spam_signals):
        try:
            create_quarantined_jsm_request(**fields, signals=spam_signals)
        except JsmAttachmentException:
            raise
        except JsmRequestException:
            logger.warning(f'Quarantine failed for support contact from {redact_email(fields["email"])}, '
                           'falling back to a normal request')
            create_jsm_request(**fields)
