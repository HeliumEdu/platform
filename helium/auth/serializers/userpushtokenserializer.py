__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from rest_framework import serializers

from helium.auth.models.userpushtoken import UserPushToken

logger = logging.getLogger(__name__)


class UserPushTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPushToken
        fields = ('id', 'created_at', 'device_id', 'token', 'user',)
