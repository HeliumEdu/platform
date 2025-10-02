__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.42"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class InfoSerializer(serializers.Serializer):
    name = serializers.CharField()

    tagline = serializers.CharField()

    version = serializers.CharField()

    support_email = serializers.EmailField()

    support_url = serializers.URLField()

    max_upload_size = serializers.IntegerField()
