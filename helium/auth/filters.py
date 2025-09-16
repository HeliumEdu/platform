__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.16"

import logging

from django_filters import rest_framework as filters

from helium.auth.models.userpushtoken import UserPushToken

logger = logging.getLogger(__name__)


class UserPushTokenFilter(filters.FilterSet):
    class Meta:
        model = UserPushToken
        fields = {
            'created_at': ['lte'],
            'device_id': ['exact'],
        }
