__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.10"

import logging

import rest_framework_simplejwt.serializers as jwt_serializers
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings

from helium.auth.tasks import blacklist_refresh_token
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class TokenObtainSerializer(jwt_serializers.TokenObtainPairSerializer):
    username = serializers.CharField(help_text="The username for the user.",
                                     label="Username")

    password = serializers.CharField(help_text="The password for the user.",
                                     label="Password", write_only=True, style={'input_type': 'password'},
                                     trim_whitespace=False)

    token = serializers.CharField(read_only=True, required=False)

    def validate(self, attrs):
        username = attrs.get('username').strip()
        password = attrs.get('password')

        if username and password:
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            if not user:
                raise serializers.ValidationError('Oops! We don\'t recognize that account. Check to make sure you '
                                                  'entered your credentials properly.', code='authorization')

            if not user.is_active or not api_settings.USER_AUTHENTICATION_RULE(user):
                raise serializers.ValidationError(
                    'Sorry, your account is not active. Check your to see if you received a verification email after '
                    'registering with us, otherwise <a href="/contact">contact us</a> and  we\'ll help you sort '
                    'this out!')

            refresh = self.get_token(user)

            attrs["refresh"] = str(refresh)
            attrs["access"] = str(refresh.access_token)

            if api_settings.UPDATE_LAST_LOGIN or self.context.get('request').data.get('last_login_now', False):
                update_last_login(None, user)

                metricutils.increment('action.user.login')

        return attrs


class TokenRefreshSerializer(jwt_serializers.TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])

        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        if user_id and (
                user := get_user_model().objects.get(
                    **{api_settings.USER_ID_FIELD: user_id}
                )
        ):
            if not api_settings.USER_AUTHENTICATION_RULE(user):
                raise AuthenticationFailed(
                    self.error_messages["no_active_account"],
                    "no_active_account",
                )

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
