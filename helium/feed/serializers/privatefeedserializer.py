__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class PrivateFeedSerializer(serializers.Serializer):
    events_private_url = serializers.URLField()

    homework_private_url = serializers.URLField()

    courseschedules_private_url = serializers.URLField()
