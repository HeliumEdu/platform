__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt import views

from helium.auth.serializers.tokenserializer import TokenRefreshSerializer, TokenObtainSerializer, \
    LegacyTokenObtainSerializer
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.token'],
    responses={
        200: TokenObtainSerializer
    }
)
class TokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    def post(self, request, *args, **kwargs):
        """
        Authenticate the user with email and password and return an access/refresh token pair.
        """
        return super().post(request, *args, **kwargs)


@extend_schema(deprecated=True, exclude=True)
class LegacyTokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    """
    Token obtain endpoint for legacy frontend that doesn't properly support token refresh.
    Uses longer token lifetimes. Excluded from API documentation.
    """
    serializer_class = LegacyTokenObtainSerializer


@extend_schema(
    tags=['auth.token'],
    responses={
        200: TokenRefreshSerializer
    }
)
class TokenRefreshView(HeliumAPIView, views.TokenRefreshView):
    def post(self, request, *args, **kwargs):
        """
        Exchange a valid refresh token for a new access token (and rotate the refresh token).
        """
        return super().post(request, *args, **kwargs)


@extend_schema(
    tags=['auth.token']
)
class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    def post(self, request, *args, **kwargs):
        """
        Takes a token and blacklists it.
        """
        return super().post(request, *args, **kwargs)
