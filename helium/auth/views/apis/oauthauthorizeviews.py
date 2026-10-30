import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.backends import JWTAuthentication
from helium.auth.serializers.oauthauthorizationserializer import (
    OAuthAuthorizationSerializer,
    OAuthDecisionSerializer,
    OAuthRedirectSerializer,
)
from helium.auth.services import oauthservice
from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


@extend_schema(tags=['auth.oauth'])
class OAuthAuthorizeView(HeliumAPIView):
    # Only the user's own signed-in session can consent; an OAuth or API token can't grant access to anything
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = OAuthDecisionSerializer

    @extend_schema(
        summary='Describe an OAuth authorization request',
        responses={status.HTTP_200_OK: OAuthAuthorizationSerializer},
    )
    def get(self, request, *args, **kwargs):
        """
        Validate an OAuth authorization request and describe it for the user's consent. Pass the request's OAuth
        parameters (`client_id`, `redirect_uri`, `response_type`, `scope`, `state`, `code_challenge`,
        `code_challenge_method`, `resource`) unchanged as this endpoint's query string.

        Show `user_email` (and its `user_oauth_providers`) on the consent screen, so the user can tell which account
        they're granting access to.

        If a `400` includes `redirect_uri`, send the user there to report the error to the client.
        """
        authorization = oauthservice.describe_authorization(request._request)
        user = request.user
        return Response(OAuthAuthorizationSerializer({
            **authorization,
            'user_email': user.email,
            'user_oauth_providers': list(user.oauth_providers.values_list('provider', flat=True)),
        }).data)

    @extend_schema(
        summary="Record the User's decision on an OAuth authorization request",
        responses={status.HTTP_200_OK: OAuthRedirectSerializer},
    )
    def post(self, request, *args, **kwargs):
        """
        Approve or deny an OAuth authorization request. Pass the request's OAuth parameters unchanged as this
        endpoint's query string. Returns the `redirect_uri` to send the user to.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        redirect_uri = oauthservice.decide_authorization(request._request, serializer.validated_data['allow'])

        return Response(OAuthRedirectSerializer({'redirect_uri': redirect_uri}).data)
