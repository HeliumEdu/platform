import logging

from rest_framework import serializers

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)


class InfoSerializer(serializers.Serializer):
    name = serializers.CharField()

    tagline = serializers.CharField()

    version = serializers.CharField()

    support_email = serializers.EmailField()

    support_url = serializers.URLField()

    max_upload_size = serializers.IntegerField()
