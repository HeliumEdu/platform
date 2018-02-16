import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.userprofileserializer import UserProfileSerializer
from helium.common.permissions import IsOwner
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class UserProfileApiDetailView(GenericAPIView):
    """
    put:
    Update the authenticated user's profile.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(user.profile, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Profile updated for user {}'.format(user.get_username()))

            metricutils.increment('action.user-profile.updated', request)

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
