import logging

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.auth.serializers.tokenserializer import TokenSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class ObtainAuthToken(GenericAPIView):
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
        return Response(serializer.data)


class DestroyAuthToken(ViewSet):
    """
    revoke:
    Revoke the authenticated user's access token.
    """
    permission_classes = (IsAuthenticated,)

    def revoke(self, request, *args, **kwargs):
        request.user.auth_token.delete()

        return Response(status=status.HTTP_200_OK)
