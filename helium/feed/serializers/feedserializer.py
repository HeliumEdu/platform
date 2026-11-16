import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


class FeedUrlsSerializer(serializers.Serializer):
    events_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the Events Feed. Prepend the API host to subscribe.',
    )

    homework_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the Assignments Feed. Prepend the API host to subscribe.',
    )

    courseschedules_private_url = serializers.URLField(
        help_text='Path (not fully-qualified URL) to the Class Schedules Feed. Prepend the API host to subscribe.',
    )
