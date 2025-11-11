__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.12.2"

import logging
from datetime import timezone

from dateutil import parser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError
from helium.planner.serializers.eventserializer import EventSerializer

logger = logging.getLogger(__name__)


class ExternalCalendarAsEventsResourceView(HeliumAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    # def get_queryset(self):
    #     if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
    #         user = self.request.user
    #         return user.external_calendars.all()
    #     else:
    #         return ExternalCalendar.objects.none()

    @extend_schema(
        parameters=[
            OpenApiParameter(name='start__gte', type=str),
            OpenApiParameter(name='end__lt', type=str),
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return an external calendar's ICAL feed items as a list of event instances.

        The IDs given for each event are sequential, unique only amongst the results of this particular query, and not
        guaranteed to be consistent across calls.
        """
        try:
            external_calendar = (ExternalCalendar.objects
                                 .for_user(request.user.id)
                                 .get(pk=self.kwargs['pk']))
        except ExternalCalendar.DoesNotExist:
            raise NotFound()

        start = parser.parse(request.query_params["start__gte"]).astimezone(
            timezone.utc) if "start__gte" in request.query_params else None
        end = parser.parse(request.query_params["end__lt"]).astimezone(
            timezone.utc) if "end__lt" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        try:
            events = icalexternalcalendarservice.calendar_to_events(external_calendar, start, end, search)
        except HeliumICalError as ex:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            raise ValidationError(ex)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
