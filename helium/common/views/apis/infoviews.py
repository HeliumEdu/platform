__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"

import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.serializers.infoserializer import InfoSerializer

logger = logging.getLogger(__name__)


class InfoResourceView(ViewSet):
    """
    info:
    Return version and configuration information about the app.
    """

    def info(self, request, *args, **kwargs):
        serializer = InfoSerializer({
            'name': settings.PROJECT_NAME,
            'tagline': settings.PROJECT_TAGLINE,
            'version': settings.PROJECT_VERSION,
            'support_email': settings.EMAIL_ADDRESS,
            'support_url': settings.SUPPORT_REDIRECT_URL,
            'bug_report_url': settings.BUG_REPORT_REDIRECT_URL,
            'max_upload_size': settings.MAX_UPLOAD_SIZE
        })

        return Response(serializer.data)
