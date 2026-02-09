__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

import rest_framework_simplejwt.serializers as jwt_serializers
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from django.db import IntegrityError
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings

from helium.auth.tasks import blacklist_refresh_token
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class TokenObtainSerializer(jwt_serializers.TokenObtainPairSerializer):
    username = serializers.CharField(help_text="The username for the user.",
                                     label="Username",
                                     write_only=True)

    password = serializers.CharField(help_text="The password for the user.",
                                     label="Password",
                                     write_only=True,
                                     style={'input_type': 'password'},
                                     trim_whitespace=False)

    access = serializers.CharField(read_only=True, required=False)

    refresh = serializers.CharField(read_only=True, required=False)

    def validate(self, attrs):
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
                    'Sorry, your account is not active. Check your to see if you received a verification email after '
                    'registering with us, otherwise <a href="/contact">contact us</a> and  we\'ll help you sort '
                    'this out!')

            try:
                token = self.get_token(user)
            except IntegrityError:
                raise PermissionDenied('Sorry, the given token is no longer valid. Request a new one.')

            attrs["access"] = str(token.access_token)
            attrs["refresh"] = str(token)

            if api_settings.UPDATE_LAST_LOGIN or self.context.get('request').data.get('last_login_now', False):
                update_last_login(None, user)

                logger.debug(f"User {username} has been logged in")

                metricutils.increment('action.user.login', request=self.context.get('request'), user=user)

        return attrs


class TokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        try:
            if user_id and (
                    user := get_user_model().objects.get(
                        **{api_settings.USER_ID_FIELD: user_id}
                    )
            ):
                if not api_settings.USER_AUTHENTICATION_RULE(user):
                    raise PermissionDenied('Sorry, your account is no longer active.')
        except get_user_model().DoesNotExist:
            raise PermissionDenied(
                'Sorry, the given token does have permissions for the given account, or the account is inactive.')

        data = {"access": str(refresh.access_token)}

        if api_settings.ROTATE_REFRESH_TOKENS:
            if api_settings.BLACKLIST_AFTER_ROTATION:
                blacklist_refresh_token.apply_async((refresh.token,),
                                                    countdown=settings.BLACKLIST_REFRESH_TOKEN_DELAY_SECS)

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
