__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

import django_filters

from helium.auth.models.userpushtoken import UserPushToken

logger = logging.getLogger(__name__)


class UserPushTokenFilter(django_filters.FilterSet):
    class Meta:
        model = UserPushToken
        fields = {
            'created_at': ['lte'],
            'device_id': ['exact'],
        }
