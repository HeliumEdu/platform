__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class ImportCreateSerializer(serializers.Serializer):
    """
    Multipart request body for importing one or more previously-exported JSON files. Files are
    sent under the repeated `file[]` field.
    """
    file = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text='One or more exported JSON files, sent as the multipart `file[]` field.'
    )


class ImportSerializer(serializers.Serializer):
    external_calendars = serializers.IntegerField()

    course_groups = serializers.IntegerField()

    courses = serializers.IntegerField()

    course_schedules = serializers.IntegerField()

    categories = serializers.IntegerField()

    resource_groups = serializers.IntegerField()

    resources = serializers.IntegerField()

    events = serializers.IntegerField()

    homework = serializers.IntegerField()

    reminders = serializers.IntegerField()

    notes = serializers.IntegerField()
