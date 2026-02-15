__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ViewSet

from helium.auth.serializers.tokenserializer import TokenResponseFieldsMixin, GoogleLoginSerializer, \
    AppleLoginSerializer
from helium.auth.services import authservice
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.google']
)
class GoogleLoginView(ViewSet, HeliumAPIView):
    serializer_class = GoogleLoginSerializer

    @extend_schema(
        request=GoogleLoginSerializer,
        responses={
            200: TokenResponseFieldsMixin
        }
    )
    def google_login(self, request, *args, **kwargs):
        """
        Authenticate or create a user via Google Sign-In using a Firebase ID token.

        If the user's email already exists in the system, they will be logged in.
        If not, a new account will be created with is_active=True (no email verification needed).
        """
        response = authservice.oauth_login(request, 'Google')

        return response


@extend_schema(
    tags=['auth.apple']
)
class AppleLoginView(ViewSet, HeliumAPIView):
    serializer_class = AppleLoginSerializer

    @extend_schema(
        request=AppleLoginSerializer,
        responses={
            200: TokenResponseFieldsMixin
        }
    )
    def apple_login(self, request, *args, **kwargs):
        """
        Authenticate or create a user via Apple Sign-In using a Firebase ID token.

        If the user's email already exists in the system, they will be logged in.
        If not, a new account will be created with is_active=True (no email verification needed).
        """
        response = authservice.oauth_login(request, 'Apple')

        return response
