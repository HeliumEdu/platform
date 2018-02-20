import logging

from django.contrib.auth import update_session_auth_hash, get_user_model
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.forms.userdeleteform import UserDeleteForm
from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import delete_user
from helium.common.permissions import IsOwner
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

logger = logging.getLogger(__name__)


class UserApiDetailView(GenericAPIView, RetrieveModelMixin):
    """
    get:
    Return the authenticated user instance, including profile and settings details.

    put:
    Update the authenticated user instance. This endpoint only updates the fields given (i.e. no need to PATCH
    for partials data).

    delete:
    Delete the authenticated user instance.
    """
    queryset = get_user_model().objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_object(self):
        return self.request.user

    def get(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(user)

        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        user = self.get_object()

        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info('User {} updated'.format(user.get_username()))

        metricutils.increment('action.user.updated', request)

        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()

        form = UserDeleteForm(user=user, data=request.data)

        if form.is_valid():
            logger.info('User {} deleted'.format(user.get_username()))

            metricutils.increment('action.user.deleted', request)

            delete_user.delay(form.user.pk)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(dict(list(form.errors.items())), status=status.HTTP_400_BAD_REQUEST)
