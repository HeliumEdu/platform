__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import logging

from rest_framework import serializers

from helium.auth.models.userpushtoken import UserPushToken

logger = logging.getLogger(__name__)


class UserPushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPushToken
        fields = ('id', 'created_at', 'device_id', 'token', 'user',)
        read_only_fields = ('user',)
