import logging

from rest_framework import serializers

from helium.planner.models.attachment import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = (
            'id', 'title', 'attachment', 'size', 'course', 'event', 'homework', 'user',)
        read_only_fields = ('size', 'user',)

    def validate(self, attrs):
        if 'course' not in attrs and 'event' not in attrs and 'homework' not in attrs:
            raise serializers.ValidationError("At least one of `course`, `event`, or `homework` must be given.")

        return attrs
