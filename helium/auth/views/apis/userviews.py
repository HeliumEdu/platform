import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.forms.userdeleteform import UserDeleteForm
from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import delete_user
from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class UserApiDetailView(HeliumAPIView, RetrieveModelMixin):
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

        return Response(serializer.data)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()

        form = UserDeleteForm(user=user, data=request.data)

        if form.is_valid():
            logger.info('User {} deleted'.format(user.get_username()))

            delete_user.delay(form.user.pk)

            data = None
            status_code = status.HTTP_204_NO_CONTENT
        else:
            data = dict(list(form.errors.items()))
            status_code = status.HTTP_400_BAD_REQUEST

        return Response(data, status=status_code)
