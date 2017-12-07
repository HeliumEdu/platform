"""
Authenticated views for UserSettings interaction.
"""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSettingsApiLUView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        serializer = UserSettingsSerializer(request.user.settings)

        return Response(serializer.data)

    def put(self, request, format=None):
        serializer = UserSettingsSerializer(request.user.settings, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Settings updated for user {}'.format(request.user.get_username()))

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
