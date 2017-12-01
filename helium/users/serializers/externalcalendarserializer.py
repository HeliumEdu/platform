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
        fields = ('title', 'url', 'color', 'shown_on_calendar',)
