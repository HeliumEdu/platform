import logging

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.feed.schemas import ExternalCalendarIDSchema
from helium.feed.services import icalexternalcalendarservice
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


class ExternalCalendarAsEventsResourceView(GenericAPIView):
    """
    get:
    Return an external calendar's ICAL feed items as a list of event instances.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ExternalCalendarIDSchema()

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def get(self, request, *args, **kwargs):
        external_calendar = self.get_object()

        calendar = icalexternalcalendarservice.validate_url(external_calendar.url)

        # TODO: add support for filtering
        external_events = icalexternalcalendarservice.calendar_to_external_events(external_calendar, calendar)

        serializer = self.get_serializer(external_events, many=True)

        return Response(serializer.data)
