import logging

from rest_framework import serializers

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class InfoSerializer(serializers.Serializer):
    name = serializers.CharField()

    tagline = serializers.CharField()

    version = serializers.CharField()

    email = serializers.EmailField()
