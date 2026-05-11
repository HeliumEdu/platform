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
    pass


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
    pass


@extend_schema(
    tags=['auth.token']
)
class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    pass
