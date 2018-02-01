import logging

from rest_framework import serializers

from helium.planner.models.attachment import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = (
            'id', 'title', 'attachment', 'size', 'course', 'event', 'homework', 'user',)
        read_only_fields = ('size', 'user',)

    def validate(self, attrs):
        if 'course' not in attrs and 'event' not in attrs and 'homework' not in attrs:
            raise serializers.ValidationError("One of `course`, `event`, or `homework` must be given.")
        elif ('course' in attrs and 'event' in attrs) or ('course' in attrs and 'homework' in attrs) or (
                        'event' in attrs and 'homework' in attrs):
            raise serializers.ValidationError("Only one of `course`, `event`, or `homework` may be given.")

        # We're settings these to None here as the serialization save will persist the new parent
        if self.instance and ('course' in attrs or 'event' in attrs or 'homework' in attrs):
            self.instance.course = None
            self.instance.event = None
            self.instance.homework = None

        return attrs
