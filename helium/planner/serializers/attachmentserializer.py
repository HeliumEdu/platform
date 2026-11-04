import logging
import os

from django.conf import settings
from django.template.defaultfilters import filesizeformat
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import FileField, IntegerField

from helium.planner.models import Attachment, Course, Homework, Event, Resource

logger = logging.getLogger(__name__)

_PARENT_FIELDS = ('course', 'event', 'homework', 'resource')


class AttachmentSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course'].queryset = Course.objects.for_user(self.context['request'].user.pk)
            self.fields['homework'].queryset = Homework.objects.for_user(self.context['request'].user.pk)
            self.fields['event'].queryset = Event.objects.for_user(self.context['request'].user.pk)
            self.fields['resource'].queryset = Resource.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Attachment
        fields = (
            'id', 'title', 'attachment', 'size', 'course', 'event', 'homework', 'resource', 'user',)
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
        parents = [field for field in _PARENT_FIELDS if attrs.get(field, None)]
        if not parents:
            raise serializers.ValidationError("One of `course`, `event`, `homework`, or `resource` must be given.")
        elif len(parents) > 1:
            raise serializers.ValidationError("Only one of `course`, `event`, `homework`, or `resource` may be given.")

        return attrs


class AttachmentCreateSerializer(serializers.Serializer):
    """
    Multipart request body for uploading one or more attachments. Files are sent under the
    repeated `file[]` field. Exactly one of `course`, `event`, `homework`, or `resource` must be supplied
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
    resource = IntegerField(required=False, help_text=Attachment._meta.get_field('resource').help_text)
