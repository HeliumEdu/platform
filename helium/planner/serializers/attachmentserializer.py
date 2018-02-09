import logging

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models.attachment import Attachment

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = (
            'id', 'title', 'attachment', 'size', 'course', 'event', 'homework', 'user',)
        read_only_fields = ('size', 'user',)

    def validate_attachment(self, attachment):
        if attachment.size > settings.MAX_UPLOAD_SIZE:
            raise ValidationError(
                'The uploaded file exceeds the max upload size of {}.'.format(filesizeformat(settings.MAX_UPLOAD_SIZE)))

        return attachment

    def validate(self, attrs):
        if 'course' not in attrs and 'event' not in attrs and 'homework' not in attrs:
            raise serializers.ValidationError("One of `course`, `event`, or `homework` must be given.")
        elif (attrs.get('course', None) and attrs.get('event', None)) or \
                (attrs.get('course', None) and attrs.get('homework', None)) or \
                (attrs.get('event', None) and attrs.get('homework', None)):
            raise serializers.ValidationError("Only one of `course`, `event`, or `homework` may be given.")

        # We're settings these to None here as the serialization save will persist the new parent
        if self.instance and ('course' in attrs or 'event' in attrs or 'homework' in attrs):
            self.instance.course = None
            self.instance.event = None
            self.instance.homework = None

        return attrs
