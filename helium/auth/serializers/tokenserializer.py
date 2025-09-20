__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.2"

import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

logger = logging.getLogger(__name__)


class TokenSerializer(TokenObtainPairSerializer):
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

        return attrs
