__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class ImportSerializer(serializers.Serializer):
    external_calendars = serializers.IntegerField()

    course_groups = serializers.IntegerField()

    courses = serializers.IntegerField()

    course_schedules = serializers.IntegerField()

    categories = serializers.IntegerField()

    material_groups = serializers.IntegerField()

    materials = serializers.IntegerField()

    events = serializers.IntegerField()

    homework = serializers.IntegerField()

    reminders = serializers.IntegerField()
