import logging

from rest_framework import status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import IsAuthenticated

from helium.auth.schemas import TokenSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.5'

logger = logging.getLogger(__name__)

from rest_framework import parsers, renderers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.response import Response
from rest_framework.views import APIView


class ObtainHeliumAuthToken(ObtainAuthToken):
    """
    post:
    Obtain an authentication token for the given user credentials. The response contains an object with a "token"
    field. The token should then be provided in the "Authorization" header with a value of "Token {token}" to all
    requests that required authentication.
    """
    parser_classes = (parsers.JSONParser,)
    schema = TokenSchema()

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)

        return Response({'token': token.key})


class DestroyHeliumAuthToken(APIView):
    """
    delete:
    Revoke the authenticated user's access token.
    """
    permission_classes = (IsAuthenticated,)

    def delete(self, request, *args, **kwargs):
        request.user.auth_token.delete()

        return Response(status=status.HTTP_200_OK)
