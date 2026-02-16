__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from rest_framework import serializers

from helium.auth.models import UserOAuthProvider


class UserOAuthProviderSerializer(serializers.ModelSerializer):
    """
    Serializer for OAuth providers linked to a user account.
    """
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)

    class Meta:
        model = UserOAuthProvider
        fields = ('id', 'provider', 'provider_display', 'created_at', 'last_used_at',)
        read_only_fields = ('id', 'provider', 'provider_display', 'created_at', 'last_used_at',)
