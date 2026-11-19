from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.backends import JWTAuthentication
from helium.auth.services import authservice
from helium.common.views.base import HeliumAPIView


@extend_schema(exclude=True)
class UserOAuthProviderSyncView(HeliumAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        """
        Update the authenticated user's sign-in providers to match the ones linked to their Firebase user.
        """
        return authservice.sync_oauth_providers(request)


@extend_schema(exclude=True)
class UserOAuthProviderApiDetailView(HeliumAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request, provider, *args, **kwargs):
        """
        Remove the given sign-in provider from the authenticated user's account and from their Firebase user. Refused
        if it is the account's only way to sign in; if Firebase can't unlink it, nothing is removed.
        """
        authservice.remove_oauth_provider(request.user, provider)

        return Response(status=status.HTTP_204_NO_CONTENT)
