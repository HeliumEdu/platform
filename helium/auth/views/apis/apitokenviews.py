__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse
from helium.auth.backends import JWTAuthentication
from helium.common.throttles import UserTokenRateThrottle
from helium.common.views.base import HeliumAPIView
from knox.models import AuthToken
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@extend_schema(tags=['auth.token.api'])
class ApiTokenView(HeliumAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (UserTokenRateThrottle,)

    @extend_schema(
        operation_id='create_api_token',
        summary="Create or rotate the authenticated User's API token",
        request=None,
        responses={
            201: OpenApiResponse(
                description='Plaintext, returned once.',
                examples=[
                    OpenApiExample(
                        'token_created',
                        value={
                            'token': 'a1b2c3d4e5f6...',
                            'created_at': '2026-05-20T12:34:56.789012Z',
                        },
                        response_only=True,
                    ),
                ],
            ),
        },
    )
    def post(self, request, *args, **kwargs):
        """
        Generate a long-lived API token. The plaintext is returned only once in this response.
        If the user already has an API token, it is invalidated and a  new
        one is issued.
        """
        AuthToken.objects.filter(user=request.user).delete()
        instance, token = AuthToken.objects.create(user=request.user)

        logger.info(f'API token created for user {request.user.pk}')

        return Response(
            {'token': token, 'created_at': instance.created},
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        operation_id='revoke_api_token',
        summary="Revoke the authenticated User's API token",
        request=None,
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        """
        Revoke the authenticated user's API token.
        """
        deleted, _ = AuthToken.objects.filter(user=request.user).delete()

        if deleted:
            logger.info(f'API token revoked for user {request.user.pk}')

        return Response(status=status.HTTP_204_NO_CONTENT)
