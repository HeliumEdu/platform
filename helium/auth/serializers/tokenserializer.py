import logging

from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2019, Helium Edu'
__version__ = '1.4.36'

logger = logging.getLogger(__name__)


class TokenSerializer(serializers.Serializer):
    username = serializers.CharField(help_text="The username or email for the user.",
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

            attrs['username'] = username
            attrs['user'] = user

            if not attrs['user'].is_active:
                raise ValidationError(
                    'Sorry, your account is not active. Check your to see if you received a verification email after '
                    'registering with us, otherwise <a href="/contact">contact us</a> and  we\'ll help you sort '
                    'this out!')

            attrs['token'], created = Token.objects.get_or_create(user=attrs['user'])
            if not created:
                attrs['token'].delete()
                attrs['token'], created = Token.objects.get_or_create(user=attrs['user'])

        return attrs
