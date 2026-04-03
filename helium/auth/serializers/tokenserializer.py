__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from datetime import timedelta

import rest_framework_simplejwt.serializers as jwt_serializers
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from helium.auth.tasks import blacklist_refresh_token
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class TokenResponseFieldsMixin(serializers.Serializer):
    """Mixin providing access and refresh token fields for response serializers."""
    access = serializers.CharField(read_only=True, required=False,
                                   help_text='JWT access token for authentication.')
    refresh = serializers.CharField(read_only=True, required=False,
                                    help_text='JWT refresh token for obtaining new access tokens.')


class TokenObtainSerializer(TokenResponseFieldsMixin, jwt_serializers.TokenObtainPairSerializer):
    username = serializers.CharField(help_text="The username for the user.",
                                     label="Username",
                                     write_only=True)

    password = serializers.CharField(help_text="The password for the user.",
                                     label="Password",
                                     write_only=True,
                                     style={'input_type': 'password'},
                                     trim_whitespace=False)

    def validate(self, attrs, update_last_login_field=True):
        username = attrs.pop('username').strip()
        password = attrs.pop('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            if not user:
                raise AuthenticationFailed('Oops! We don\'t recognize that account. Check to make sure you '
                                           'entered your credentials properly.')

            if not api_settings.USER_AUTHENTICATION_RULE(user):
                raise PermissionDenied(
                    detail={
                        'detail': 'Sorry, your account is not active. Check your to see if you received a '
                                  'verification email after registering with us.',
                        'code': 'account_inactive',
                        'username': username,
                    }
                )

            try:
                token = self.get_token(user)
            except IntegrityError:
                raise PermissionDenied('Sorry, the given token is no longer valid. Request a new one.')

            attrs["access"] = str(token.access_token)
            attrs["refresh"] = str(token)

            if update_last_login_field:
                update_last_login(None, user)

            user.last_activity = timezone.now()
            user.deletion_warning_count = 0
            user.deletion_warning_sent_at = None
            user.save(update_fields=['last_activity', 'deletion_warning_count', 'deletion_warning_sent_at'])

            if not user.settings.next_review_prompt_date:
                user.settings.next_review_prompt_date = (
                    timezone.now() + timedelta(days=settings.REVIEW_PROMPT_INITIAL_DELAY_DAYS)
                )
                user.settings.save(update_fields=['next_review_prompt_date'])

            self._authenticated_user = user

            logger.debug(f"User {user.pk} has been logged in")

            metricutils.increment('action.user.login', request=self.context.get('request'), user=user)

        return attrs


class LegacyAccessToken(AccessToken):
    """Access token with legacy (longer) lifetime for legacy frontend."""
    lifetime = timedelta(minutes=settings.LEGACY_ACCESS_TOKEN_TTL_MINUTES)


class LegacyRefreshToken(RefreshToken):
    """Refresh token with legacy (longer) lifetime for legacy frontend."""
    lifetime = timedelta(days=settings.LEGACY_REFRESH_TOKEN_TTL_DAYS)
    access_token_class = LegacyAccessToken


class LegacyTokenObtainSerializer(TokenObtainSerializer):
    """
    Token obtain serializer for legacy frontend that doesn't properly support token refresh.
    Uses longer token lifetimes configured via LEGACY_*_TTL settings.

    Deprecated: Remove when frontend-legacy is shut down.
    """

    @classmethod
    def get_token(cls, user):
        return LegacyRefreshToken.for_user(user)

    def validate(self, attrs):
        attrs = super().validate(attrs, update_last_login_field=False)

        if user := getattr(self, '_authenticated_user', None):
            user.last_login_legacy = timezone.now()
            user.save(update_fields=['last_login_legacy'])

        return attrs


class TokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    def validate(self, attrs):
        UserModel = get_user_model()

        refresh = self.token_class(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        user = None
        try:
            if user_id and (
                    user := UserModel.objects.get(
                        **{api_settings.USER_ID_FIELD: user_id}
                    )
            ):
                if not api_settings.USER_AUTHENTICATION_RULE(user):
                    raise PermissionDenied('Sorry, your account is no longer active.')
        except UserModel.DoesNotExist:
            raise PermissionDenied(
                'Sorry, the given token does have permissions for the given account, or the account is inactive.')

        if user:
            user.last_activity = timezone.now()
            user.deletion_warning_count = 0
            user.deletion_warning_sent_at = None
            user.save(update_fields=['last_activity', 'deletion_warning_count', 'deletion_warning_sent_at'])

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                blacklist_refresh_token.apply_async(
                    (refresh.token,),
                    countdown=settings.BLACKLIST_REFRESH_TOKEN_DELAY_SECS,
                    priority=settings.CELERY_PRIORITY_LOW,
                )

            refresh.set_jti()
            refresh.set_exp()
            refresh.set_iat()
            refresh.outstand()

            data["refresh"] = str(refresh)

        return data


class TokenBlacklistSerializer(jwt_serializers.TokenBlacklistSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])

        try:
            refresh.blacklist()
        except AttributeError:
            pass
        except IntegrityError:
            logger.info("IntegrityError, parent token was already blacklisted or purge, nothing to do.")
        return {}


class OAuthLoginSerializer(serializers.Serializer):
    """Serializer for OAuth Sign-In via Firebase ID token."""
    id_token = serializers.CharField(
        help_text='Firebase ID token obtained from OAuth Sign-In on the client.',
        write_only=True
    )
    provider = serializers.ChoiceField(
        choices=['google', 'apple'],
        help_text='The OAuth provider (google or apple).',
        write_only=True
    )
