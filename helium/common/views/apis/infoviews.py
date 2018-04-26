import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.serializers.infoserializer import InfoSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.9'

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
            'max_upload_size': settings.MAX_UPLOAD_SIZE
        })

        return Response(serializer.data)
