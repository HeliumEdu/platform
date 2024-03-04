__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class PrivateFeedSerializer(serializers.Serializer):
    events_private_url = serializers.URLField()

    homework_private_url = serializers.URLField()

    courseschedules_private_url = serializers.URLField()
