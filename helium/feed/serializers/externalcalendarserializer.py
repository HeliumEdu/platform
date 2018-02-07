from future.standard_library import install_aliases

from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError

install_aliases()
import logging
from rest_framework import serializers

from helium.feed.models import ExternalCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class ExternalCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalCalendar
        fields = ('id', 'title', 'url', 'color', 'shown_on_calendar', 'user',)
        read_only_fields = ('user',)

    def validate_url(self, url):
        """
        Ensure a valid ICAL URL is given.

        :param url: the URL to validate
        :return: the validated URL
        """
        if self.instance and url == self.instance.url:
            return url

        try:
            icalexternalcalendarservice.validate_url(url)

            return url
        except HeliumICalError as ex:
            logger.info("Unable to validate external ICAL URL {}: {}".format(url, ex))

            raise serializers.ValidationError(ex)
