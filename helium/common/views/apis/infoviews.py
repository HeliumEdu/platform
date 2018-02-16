import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.common.serializers.infoserializer import InfoSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class InfoView(APIView):
    """
    get:
    Return information about the app.
    """

    def get(self, request, *args, **kwargs):
        serializer = InfoSerializer({
            'name': settings.PROJECT_NAME,
            'tagline': settings.PROJECT_TAGLINE,
            'version': settings.PROJECT_VERSION,
            'email': settings.EMAIL_ADDRESS,
        })

        return Response(serializer.data)
