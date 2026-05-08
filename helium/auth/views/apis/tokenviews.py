__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework_simplejwt import views

from helium.auth.serializers.tokenserializer import TokenRefreshSerializer, TokenObtainSerializer
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=['auth.token.jwt'])
class TokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    @extend_schema(
        operation_id='login',
        summary='Log in and obtain a token pair',
        responses={200: TokenObtainSerializer},
        examples=[
            OpenApiExample(
                'login_with_email',
                summary='Log in with an email address',
                value={
                    'email': 'student@example.com',
                    'password': 'correct horse battery staple',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """
        Authenticate the user with email and password and return an access/refresh token pair.
        """
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['auth.token'])
class TokenRefreshView(HeliumAPIView, views.TokenRefreshView):
    @extend_schema(
        operation_id='token_refresh',
        summary='Refresh an access token',
        responses={200: TokenRefreshSerializer},
        description=(
            "Exchange a valid refresh token for a new access token (and rotate the refresh "
            "token).\n\n"
            "A `401` response with body `{\"code\": \"token_not_valid\", ...}` on any other "
            "endpoint means the access token has expired. POST the current refresh token here, "
            "replace the access token with the response's `access`, and retry the original "
            "request. The refresh endpoint also rotates the refresh token, so always store the "
            "most recently returned `refresh` value and use it on the next refresh call.\n\n"
            "Refresh proactively a minute or two before `access_token_lifetime_minutes` "
            "elapses to avoid an extra round-trip per request.\n\n"
            "Example refresh cycle (pseudo-curl):\n\n"
            "```\n"
            "# 1. Initial login\n"
            "curl -X POST https://api.heliumedu.com/auth/token/ \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"email\": \"student@example.com\", \"password\": \"...\"}'\n"
            "# Returns: {\"access\": \"<A1>\", \"refresh\": \"<R1>\"}\n"
            "\n"
            "# 2. Refresh shortly before the access token expires\n"
            "curl -X POST https://api.heliumedu.com/auth/token/refresh/ \\\n"
            "  -H 'Content-Type: application/json' \\\n"
            "  -d '{\"refresh\": \"<R1>\"}'\n"
            "# Returns: {\"access\": \"<A2>\", \"refresh\": \"<R2>\"} -- use R2 next, NOT R1\n"
            "\n"
            "# 3. Continue with Authorization: Bearer <A2>\n"
            "```"
        ),
    )
    def post(self, request, *args, **kwargs):
        """
        Exchange a valid refresh token for a new access token (and rotate the refresh token).
        """
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['auth.token.jwt'])
class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    @extend_schema(operation_id='logout', summary='Log out and blacklist a refresh token')
    def post(self, request, *args, **kwargs):
        """
        Log out the user and blacklist the given refresh token.
        """
        return super().post(request, *args, **kwargs)
