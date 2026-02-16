__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.viewsets import ViewSet

from helium.auth.serializers.tokenserializer import TokenResponseFieldsMixin, OAuthLoginSerializer
from helium.auth.services import authservice
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['auth.oauth']
)
class OAuthLoginView(ViewSet, HeliumAPIView):
    serializer_class = OAuthLoginSerializer

    @extend_schema(
        request=OAuthLoginSerializer,
        responses={
            200: TokenResponseFieldsMixin
        }
    )
    def oauth_login(self, request, *args, **kwargs):
        """
        Authenticate or create a user via OAuth Sign-In using a Firebase ID token.

        Supports Google and Apple Sign-In. If the user's email already exists in the system,
        they will be logged in. If not, a new account will be created with is_active=True
        (no email verification needed).
        """
        response = authservice.oauth_login(request)

        return response
