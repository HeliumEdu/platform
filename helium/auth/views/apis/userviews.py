__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError, AuthenticationFailed
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import delete_user
from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView

logger = logging.getLogger(__name__)


class UserApiDetailView(HeliumAPIView, RetrieveModelMixin):
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        """
        Return the authenticated user instance, including profile and settings details.
        """
        user = self.get_object()

        serializer = self.get_serializer(user)

        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        """
        Update the authenticated user instance. This endpoint only updates the fields given (i.e. no need to PATCH
        for partials data).
        """
        user = self.get_object()

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(f'User {user.get_username()} updated')

        return Response(serializer.data)


class UserDeleteResourceView(HeliumAPIView):
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def delete(self, request, *args, **kwargs):
        """
        Delete the given user instance. The request body should include the authenticated user's `password` for the
        request to succeed.
        """
        user = self.get_object()

        if 'password' not in request.data:
            raise ValidationError({'password': ['This field is required.']})

        if not user.check_password(request.data['password']):
            raise ValidationError({'password': ['The password is incorrect.']})

        logger.info(f'User {user.get_username()} will be deleted')

        delete_user.delay(user.pk)

        return Response(status=status.HTTP_204_NO_CONTENT)


class UserDeleteInactiveResourceView(HeliumAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        try:
            return get_user_model().objects.get(username=self.request.data['username'])
        except get_user_model().DoesNotExist:
            raise NotFound('No User matches the given query.')

    def delete(self, request, *args, **kwargs):
        """
        Delete an inactive user instance. The request body should include the `username` and `password`, and this route
        can only be used to delete users that never finished setting up their account.
        """
        if 'username' not in request.data:
            raise ValidationError({'username': ['This field is required.']})

        if 'password' not in request.data:
            raise ValidationError({'password': ['This field is required.']})

        user = self.get_object()

        if user.is_active:
            raise ValidationError({'non_field_errors': ['This endpoint can only be used to cleanup user accounts that '
                                                  'were never activated.']})

        if not user.check_password(request.data['password']):
            raise AuthenticationFailed({'password': ['The password is incorrect.']})

        logger.info(f'User {user.get_username()} will be deleted')

        delete_user.delay(user.pk)

        return Response(status=status.HTTP_204_NO_CONTENT)
