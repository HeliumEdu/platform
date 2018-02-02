import logging

from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.feed.schemas import ExternalCalendarIDSchema
from helium.feed.services import icalservice
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendarAsExternalEventsView(GenericAPIView):
    """
    get:
    Return a list of all external event instances for the given external calendar's feed.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ExternalCalendarIDSchema()

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def get(self, request, *args, **kwargs):
        external_calendar = self.get_object()

        calendar = icalservice.validate_url(external_calendar.url)

        # TODO: add support to filter by a start/end date as well as other filters
        external_events = icalservice.calendar_to_external_events(external_calendar, calendar)

        serializer = self.get_serializer(external_events, many=True)

        return Response(serializer.data)
