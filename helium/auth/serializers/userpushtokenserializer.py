import logging

from rest_framework import serializers

from helium.auth.models.userpushtoken import UserPushToken

logger = logging.getLogger(__name__)


class UserPushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPushToken
        fields = ('id', 'created_at', 'device_id', 'token', 'platform', 'user',)
        read_only_fields = ('platform', 'user',)
