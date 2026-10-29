import logging

from rest_framework import serializers

from helium.auth.serializers.oauthauthorizationserializer import OAuthScopeSerializer

logger = logging.getLogger(__name__)


class ConnectedAppSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text='The connected app.')

    name = serializers.CharField(help_text="The app's name.")

    scopes = OAuthScopeSerializer(many=True, help_text='The scopes the app holds.')

    last_used_at = serializers.DateTimeField(allow_null=True,
                                             help_text='When the app last obtained an access token.')
