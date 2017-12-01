"""
ExternalCalendar serializer.
"""
import logging

from rest_framework import serializers

from helium.users.models import ExternalCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalCalendar
        fields = ('id', 'title', 'url', 'color', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user

        return super(ExternalCalendarSerializer, self).create(validated_data)
