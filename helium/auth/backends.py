__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.utils.translation import gettext_lazy as _
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import AUTH_HEADER_TYPE_BYTES
from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.utils import get_md5_hash_password


_AUTH_HEADER_TYPE_BYTES_LOWER = {prefix.lower() for prefix in AUTH_HEADER_TYPE_BYTES}


class JWTAuthenticationScheme(SimpleJWTScheme):
    """Tell drf-spectacular that our subclass uses the same JWT security scheme as the simplejwt base."""
    target_class = 'helium.auth.backends.JWTAuthentication'


class ApiTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'knox.auth.TokenAuthentication'
    name = 'apiToken'
    priority = 1

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'token',
        }


class JWTAuthentication(BaseJWTAuthentication):
    def get_raw_token(self, header):
        """
        simplejwt's base implementation matches the auth scheme prefix with a strict byte
        comparison against ``AUTH_HEADER_TYPES``, rejecting clients that send a differently-cased
        prefix (e.g. ``authorization: bearer ...``). RFC 7235 §2.1 specifies that the scheme
        token is case-insensitive, so accept any casing.
        """
        parts = header.split()
        if len(parts) == 0:
            return None
        if parts[0].lower() not in _AUTH_HEADER_TYPE_BYTES_LOWER:
            return None
        if len(parts) != 2:
            raise AuthenticationFailed(
                _("Authorization header must contain two space-delimited values"),
                code="bad_authorization_header",
            )
        return parts[1]

    def get_user(self, validated_token):
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken(_("Token contained no recognizable user identification"))

        try:
            user = (self.user_model.objects
                    .select_related('settings')
                    .get(**{api_settings.USER_ID_FIELD: user_id}))
        except self.user_model.DoesNotExist:
            raise AuthenticationFailed(_("User not found"), code="user_not_found")

        if api_settings.CHECK_USER_IS_ACTIVE and not user.is_active:
            raise AuthenticationFailed(_("User is inactive"), code="user_inactive")

        if api_settings.CHECK_REVOKE_TOKEN:
            if validated_token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
                raise AuthenticationFailed(_("The user's password has been changed."), code="password_changed")

        return user
