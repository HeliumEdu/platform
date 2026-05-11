__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import os

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import FileField, IntegerField

from helium.planner.models import Attachment, Course, Homework, Event

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
                f'The uploaded file exceeds the max upload size of {filesizeformat(settings.MAX_UPLOAD_SIZE)}.')

        ext = os.path.splitext(attachment.name)[1].lower()
        if ext in settings.BLOCKED_ATTACHMENT_EXTENSIONS:
            raise ValidationError('This file type is not allowed.')

        if attachment.content_type in settings.BLOCKED_ATTACHMENT_MIME_TYPES:
            raise ValidationError('This file type is not allowed.')

        return attachment

    def validate(self, attrs):
        if 'course' not in attrs and 'event' not in attrs and 'homework' not in attrs:
            raise serializers.ValidationError("One of `course`, `event`, or `homework` must be given.")
        elif (attrs.get('course', None) and attrs.get('event', None)) or \
                (attrs.get('course', None) and attrs.get('homework', None)) or \
                (attrs.get('event', None) and attrs.get('homework', None)):
            raise serializers.ValidationError("Only one of `course`, `event`, or `homework` may be given.")

        return attrs


class AttachmentCreateSerializer(serializers.Serializer):
    """
    Multipart request body for uploading one or more attachments. Files are sent under the
    repeated `file[]` field. Exactly one of `course`, `event`, or `homework` must be supplied
    to associate the uploaded files with their owning entity.
    """
    file = serializers.ListField(
        child=FileField(),
        required=True,
        help_text='One or more files, sent as the multipart `file[]` field.'
    )
    course = IntegerField(required=False, help_text=Attachment._meta.get_field('course').help_text)
    event = IntegerField(required=False, help_text=Attachment._meta.get_field('event').help_text)
    homework = IntegerField(required=False, help_text=Attachment._meta.get_field('homework').help_text)
