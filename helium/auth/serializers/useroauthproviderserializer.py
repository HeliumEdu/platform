__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from rest_framework import serializers

from helium.auth.models import UserOAuthProvider


class UserOAuthProviderSerializer(serializers.ModelSerializer):
    """
    An OAuth provider linked to a user account.
    """
    provider_display = serializers.CharField(source='get_provider_display', read_only=True)

    class Meta:
        model = UserOAuthProvider
        fields = ('id', 'provider', 'provider_display', 'created_at', 'last_used_at',)
        read_only_fields = ('id', 'provider', 'provider_display', 'created_at', 'last_used_at',)
