__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.51"

import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from helium.common.serializers.infoserializer import InfoSerializer
from helium.common.views.views import HeliumAPIView

logger = logging.getLogger(__name__)


class InfoResourceView(GenericViewSet, HeliumAPIView):
    serializer_class = InfoSerializer

    def info(self, request, *args, **kwargs):
        """
        Return version and configuration information about the app.
        """
        serializer = InfoSerializer({
            'name': settings.PROJECT_NAME,
            'tagline': settings.PROJECT_TAGLINE,
            'version': settings.PROJECT_VERSION,
            'support_email': settings.EMAIL_ADDRESS,
            'support_url': settings.SUPPORT_REDIRECT_URL,
            'max_upload_size': settings.MAX_UPLOAD_SIZE
        })

        return Response(serializer.data)
