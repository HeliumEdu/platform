import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class OAuthScopeSerializer(serializers.Serializer):
    scope = serializers.CharField(help_text='The scope name.')

    description = serializers.CharField(help_text='What the scope allows, shown to the user.')


class OAuthAuthorizationSerializer(serializers.Serializer):
    client_name = serializers.CharField(help_text='The name of the client requesting access.')

    redirect_uri = serializers.CharField(help_text="The client's redirect URI.")

    scopes = OAuthScopeSerializer(many=True, help_text='The scopes requested.')

    user_email = serializers.EmailField(help_text='The signed-in User the access would be granted for.')


class OAuthDecisionSerializer(serializers.Serializer):
    allow = serializers.BooleanField(help_text='`true` to approve the request, `false` to deny it.')


class OAuthRedirectSerializer(serializers.Serializer):
    redirect_uri = serializers.CharField(help_text="The client's redirect URI, with the authorization code or the denial.")
