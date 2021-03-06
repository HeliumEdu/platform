import logging

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.schemas import ExternalCalendarIDSchema
from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class ExternalCalendarAsEventsResourceView(HeliumAPIView):
    """
    get:
    Return an external calendar's ICAL feed items as a list of event instances.

    The IDs given for each event are sequential, unique only amongst the results of this particular query, and not
    guaranteed to be consistent across calls.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ExternalCalendarIDSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    def get(self, request, *args, **kwargs):
        external_calendar = self.get_object()

        try:
            # TODO: add support for filtering
            events = icalexternalcalendarservice.calendar_to_events(external_calendar)
        except HeliumICalError as ex:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            raise ValidationError(ex)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
