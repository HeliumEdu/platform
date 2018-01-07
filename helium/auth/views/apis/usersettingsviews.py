import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserSettingsApiDetailView(GenericAPIView):
    """
    put:
    Update the given (and authenticated) user's settings.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, pk, format=None):
        # This call gets the object and checks permissions
        self.get_object()

        serializer = self.get_serializer(request.user.settings, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Settings updated for user {}'.format(request.user.get_username()))

            metricutils.increment('action.user-settings.updated', request)

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
