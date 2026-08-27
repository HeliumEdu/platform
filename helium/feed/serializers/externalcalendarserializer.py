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

    def _is_url_changing(self, attrs):
        return 'url' in attrs and (not self.instance or attrs['url'] != self.instance.url)

    def _is_being_reenabled(self, attrs):
        return (self.instance
                and not self.instance.shown_on_calendar
                and attrs.get('shown_on_calendar') is True)

    def validate(self, attrs):
        url = attrs.get('url', None)
        if not url and self.instance:
            url = self.instance.url

        if url and (self._is_url_changing(attrs) or self._is_being_reenabled(attrs)):
            try:
                icalexternalcalendarservice.validate_url(url)
            except HeliumICalError as e:
                raise serializers.ValidationError({'url': str(e)})

        return attrs

    def update(self, instance, validated_data):
        invalidate_cache = (self._is_url_changing(validated_data)
                            or self._is_being_reenabled(validated_data))

        instance = super().update(instance, validated_data)

        if invalidate_cache:
            icalexternalcalendarservice.invalidate_calendar_cache(instance)

        return instance
