__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.7"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework_simplejwt import views

from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.token']
)
class TokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    pass


@extend_schema(
    tags=['auth.token']
)
class TokenRefreshView(HeliumAPIView, views.TokenRefreshView):
    pass


@extend_schema(
    tags=['auth.token']
)
class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    pass
