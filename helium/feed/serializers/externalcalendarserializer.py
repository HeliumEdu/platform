"""
ExternalCalendar serializer.
"""
from future.standard_library import install_aliases

install_aliases()
import logging
from urllib.request import urlopen
from rest_framework import serializers
from rest_framework import status

from helium.feed.models import ExternalCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2015, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalCalendar
        fields = ('id', 'title', 'url', 'color', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)

    def validate_url(self, url):
        """
        Ensure a valid Google Calendar URL is given.

        :param url: the URL to validate
        :return: the validated URL
        """
        if urlopen(url).getcode() != status.HTTP_200_OK:
            serializers.ValidationError("The URL is not reachable.")

        # TODO: parse the URL to validate it is, in fact, an valid ICAL feed

        return url
