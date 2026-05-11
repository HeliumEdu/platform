__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt import views

from helium.auth.serializers.tokenserializer import TokenRefreshSerializer, TokenObtainSerializer
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=['auth.token'])
class TokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    @extend_schema(
        operation_id='login',
        responses={200: TokenObtainSerializer},
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
        responses={200: TokenRefreshSerializer},
    )
    def post(self, request, *args, **kwargs):
        """
        Exchange a valid refresh token for a new access token (and rotate the refresh token).
        """
        return super().post(request, *args, **kwargs)


@extend_schema(tags=['auth.token'])
class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    @extend_schema(operation_id='logout')
    def post(self, request, *args, **kwargs):
        """
        Takes a token and blacklists it.
        """
        return super().post(request, *args, **kwargs)
