import logging

from drf_spectacular.utils import extend_schema
from oauth2_provider.models import get_application_model
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.backends import JWTAuthentication
from helium.auth.serializers.connectedappserializer import ConnectedAppSerializer
from helium.auth.services import oauthservice
from helium.auth.services.tokenservice import revoke_oauth_tokens
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=['auth.oauth'])
class UserConnectedAppApiListView(HeliumAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = ConnectedAppSerializer

    @extend_schema(
        operation_id='list_connected_apps',
        summary="List the authenticated User's connected apps",
        responses={status.HTTP_200_OK: ConnectedAppSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        """
        Return the apps the authenticated user has granted access to with OAuth that can still act for them, most
        recently used first.
        """
        apps = oauthservice.connected_apps(request.user)

        page = self.paginate_queryset(apps)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)

        return Response(self.get_serializer(apps, many=True).data)


@extend_schema(tags=['auth.oauth'])
class UserConnectedAppApiDetailView(HeliumAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id='revoke_connected_app',
        summary="Revoke one of the authenticated User's connected apps",
        request=None,
        responses={status.HTTP_204_NO_CONTENT: None},
    )
    def delete(self, request, pk, *args, **kwargs):
        """
        Revoke the given app's access to the authenticated user's account: its access tokens, refresh tokens, and
        unused authorization codes.
        """
        if not any(app['id'] == pk for app in oauthservice.connected_apps(request.user)):
            raise NotFound('No connected app matches the given query.')

        revoke_oauth_tokens(request.user, get_application_model().objects.get(pk=pk))
        logger.info(f'Connected app {pk} revoked for user {request.user.pk}')

        return Response(status=status.HTTP_204_NO_CONTENT)
