import logging

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.userprofileserializer import UserProfileSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserProfileApiDetailView(GenericAPIView):
    """
    put:

    Update the given (and authenticated) user's profile.
    """
    serializer_class = UserProfileSerializer
    permission_classes = (IsAuthenticated,)

    def put(self, request, pk, format=None):
        if int(pk) != request.user.pk:
            self.permission_denied(request, 'You do not have permission to perform this action.')

        serializer = self.get_serializer(request.user.profile, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Profile updated for user {}'.format(request.user.get_username()))

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
