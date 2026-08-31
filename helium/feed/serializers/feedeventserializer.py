import logging

from rest_framework import serializers

from helium.planner.serializers.eventserializer import EventSerializer

logger = logging.getLogger(__name__)


class FeedEventSerializer(EventSerializer):
    """An external calendar's events, which own none of the relations a planner event can.

    A feed event is built in memory and never saved, so nothing can reference it, but the
    synthetic id it carries is non-null and Django would query on its behalf regardless.
    """

    attachments = serializers.SerializerMethodField()
    reminders = serializers.SerializerMethodField()
    notes = serializers.SerializerMethodField()

    def get_attachments(self, obj) -> list:
        return []

    def get_reminders(self, obj) -> list:
        return []

    def get_notes(self, obj) -> list:
        return []
