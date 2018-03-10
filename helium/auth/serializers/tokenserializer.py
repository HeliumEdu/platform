import logging

from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.exceptions import ValidationError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

logger = logging.getLogger(__name__)


class TokenSerializer(AuthTokenSerializer):
    username = serializers.CharField(help_text="The username or email for the user.",
                                     label="Username", write_only=True)
    password = serializers.CharField(help_text="The password for the user.",
                                     label="Password", write_only=True, style={'input_type': 'password'},
                                     trim_whitespace=False)
    token = serializers.CharField(read_only=True, required=False)

    def validate(self, attrs):
        attrs = super(TokenSerializer, self).validate(attrs)

        if not attrs['user'].is_active:
            raise ValidationError('This account is not active.')

        attrs['token'], created = Token.objects.get_or_create(user=attrs['user'])
        if not created:
            attrs['token'].delete()
            attrs['token'], created = Token.objects.get_or_create(user=attrs['user'])

        return attrs
