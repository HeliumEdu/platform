__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from rest_framework_simplejwt import views

from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


class TokenObtainPairView(HeliumAPIView, views.TokenObtainPairView):
    pass


class TokenRefreshView(HeliumAPIView, views.TokenRefreshView):
    pass


class TokenBlacklistView(HeliumAPIView, views.TokenBlacklistView):
    pass
