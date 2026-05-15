__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class ImportCreateSerializer(serializers.Serializer):
    """
    Multipart request body for importing a previously-exported JSON file. Exactly one file must
    be uploaded per request, sent under the `file[]` field.
    """
    file = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text='A previously-exported JSON file, sent as the multipart `file[]` field. Exactly one file per request.'
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
