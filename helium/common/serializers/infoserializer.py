__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class InfoSerializer(serializers.Serializer):
    name = serializers.CharField()

    tagline = serializers.CharField()

    version = serializers.CharField()

    support_email = serializers.EmailField()

    support_url = serializers.URLField()

    bug_report_url = serializers.URLField()

    max_upload_size = serializers.IntegerField()
