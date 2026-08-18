__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

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
