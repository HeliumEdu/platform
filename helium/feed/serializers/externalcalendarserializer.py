__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError

logger = logging.getLogger(__name__)


class ExternalCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalCalendar
        fields = ('id', 'title', 'url', 'color', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)

    def validate(self, attrs):
        url = attrs.get('url', None)
        if not url and self.instance:
            url = self.instance.url

        if url and (not self.instance or (self.instance and url != self.instance.url)):
            try:
                icalexternalcalendarservice.validate_url(url)
            except HeliumICalError as e:
                raise serializers.ValidationError({'url': str(e)})

        return attrs

    def update(self, instance, validated_data):
        url_changed = 'url' in validated_data and validated_data['url'] != instance.url

        instance = super().update(instance, validated_data)

        if url_changed:
            icalexternalcalendarservice.invalidate_calendar_cache(instance)

        return instance
