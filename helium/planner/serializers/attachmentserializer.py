"""
Attachment serializer.
"""
import logging

from rest_framework import serializers

from helium.planner.models.attachment import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = (
            'id', 'title', 'attachment', 'size', 'course',)
        read_only_fields = ('size',)
