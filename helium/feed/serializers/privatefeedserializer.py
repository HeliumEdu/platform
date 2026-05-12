__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class PrivateFeedSerializer(serializers.Serializer):
    events_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the events iCal feed. Prepend the API host to subscribe.',
    )

    homework_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the homework iCal feed. Prepend the API host to subscribe.',
    )

    courseschedules_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the course-schedules iCal feed. Prepend the API host to subscribe.',
    )
