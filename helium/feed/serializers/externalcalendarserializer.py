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

    def validate(self, attrs):
        """
        Ensure a valid ICAL URL is given. If not, disable the calendar.

        :param attrs: the data to be saved
        :return: the validated data
        """
        url = attrs.get('url', None)
        if not url and self.instance:
            url = self.instance.url

        if url and (not self.instance or (self.instance and url != self.instance.url)):
            try:
                icalexternalcalendarservice.validate_url(url)
            except HeliumICalError:
                logger.info("Unable to validate external ICAL URL {}, so disabling the calendar.")

                if self.instance:
                    self.instance.shown_on_calendar = False
                    self.instance.save()
                else:
                    attrs['shown_on_calendar'] = False

        return attrs
