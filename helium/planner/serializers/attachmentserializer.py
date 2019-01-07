import logging

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models import Attachment, Course, Homework, Event

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)


class AttachmentSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)
            self.fields['homework'].queryset = Homework.objects.for_user(self.context['request'].user.pk)
            self.fields['event'].queryset = Event.objects.for_user(self.context['request'].user.pk)

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

        return attrs
