import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.auth.serializers.tokenserializer import TokenSerializer
from helium.common.views.views import HeliumAPIView

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class ObtainTokenResourceView(HeliumAPIView):
    """
    post:
    Obtain an authentication token for the given user credentials. The "token" in the response should then be provided
    in all future calls that required authentication. This can be done by setting the `Authorization` header with a
    value of `Token <token>`.
    """
    serializer_class = TokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})

        serializer.is_valid(raise_exception=True)

        user = get_user_model().objects.get_by_natural_key(serializer.data['username'])
        user_logged_in.send(sender=user.__class__, request=request, user=user)

        return Response(serializer.data)


class DestroyTokenResourceView(ViewSet, HeliumAPIView):
    """
    revoke:
    Revoke the authenticated user's access token.
    """
    permission_classes = (IsAuthenticated,)

    def revoke(self, request, *args, **kwargs):
        request.user.auth_token.delete()

        return Response()
