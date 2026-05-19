__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
from typing import List

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.template.defaultfilters import filesizeformat
from rest_framework import serializers

SUPPORT_CATEGORIES = ('Bug Report', 'Feature Request', 'Account Issue')


class SupportContactSerializer(serializers.Serializer):
    """
    Shape of an inbound support contact request: a subject, the submitter's email,
    a category, a description, and optional file attachments.
    """
    subject = serializers.CharField(max_length=200, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    category = serializers.ChoiceField(choices=SUPPORT_CATEGORIES)
    description = serializers.CharField(max_length=10000, trim_whitespace=True)
    attachment = serializers.ListField(
        child=serializers.FileField(),
        required=False,
        default=list,
        help_text='Optional file attachments, sent as the multipart `attachment` field.',
    )
    website = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_attachment(self, attachments: List[UploadedFile]) -> List[UploadedFile]:
        """
        Reject attachments that exceed the upload size limit or whose extension
        or MIME type is in the configured blocked lists.

        :param attachments: Files submitted under the ``attachment`` multipart field.
        :return: The same list, unchanged, once every file has been validated.
        :raises serializers.ValidationError: If any file is too large or has a blocked type.
        """
        for f in attachments:
            if f.size > settings.MAX_UPLOAD_SIZE:
                raise serializers.ValidationError(
                    f'Attachment "{f.name}" exceeds the max upload size of '
                    f'{filesizeformat(settings.MAX_UPLOAD_SIZE)}.'
                )

            ext = os.path.splitext(f.name)[1].lower()
            if ext in settings.BLOCKED_ATTACHMENT_EXTENSIONS:
                raise serializers.ValidationError(f'Attachment "{f.name}" file type is not allowed.')

            if getattr(f, 'content_type', None) in settings.BLOCKED_ATTACHMENT_MIME_TYPES:
                raise serializers.ValidationError(f'Attachment "{f.name}" file type is not allowed.')

        return attachments
