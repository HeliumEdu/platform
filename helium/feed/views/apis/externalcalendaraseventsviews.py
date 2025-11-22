__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.28"

import logging
from datetime import datetime, timezone

from dateutil import parser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.views.base import HeliumCalendarItemAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.externalcalendar.event', 'calendar.user']
)
class UserExternalCalendarAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return all external calendar's that should be shown on the calendar for the authenticated user as a list of ExternalCalendar Event instances.

        The IDs given for each ExternalCalendar Event are sequential, unique only amongst the results of this
        particular query, and not guaranteed to be consistent across calls.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        user = request.user
        external_calendars = (ExternalCalendar.objects
                              .for_user(user.pk))
        if 'shown_on_calendar' in request.query_params:
            external_calendars = external_calendars.filter(shown_on_calendar=request.query_params['shown_on_calendar'].lower() == 'true')

        _from = parser.parse(request.query_params["from"]).astimezone(timezone.utc) \
            if "from" in request.query_params else None
        to = parser.parse(request.query_params["to"]).astimezone(timezone.utc) \
            if "to" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        try:
            events = []
            for external_calendar in external_calendars:
                events += icalexternalcalendarservice.calendar_to_events(external_calendar, _from, to, search)
        except HeliumICalError as ex:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            raise ValidationError(ex)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)


@extend_schema(
    tags=['feed.externalcalendar.event']
)
class ExternalCalendarAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return an external calendar's ICAL feed items as a list of ExternalCalendar Event instances.

        The IDs given for each ExternalCalendar Event are sequential, unique only amongst the results of this
        particular query, and not guaranteed to be consistent across calls.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        try:
            external_calendar = (ExternalCalendar.objects
                                 .for_user(request.user.id)
                                 .get(pk=self.kwargs['pk']))
        except ExternalCalendar.DoesNotExist:
            raise NotFound()

        _from = parser.parse(request.query_params["from"]).astimezone(timezone.utc) \
            if "from" in request.query_params else None
        to = parser.parse(request.query_params["to"]).astimezone(timezone.utc) \
            if "to" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        try:
            events = icalexternalcalendarservice.calendar_to_events(external_calendar, _from, to, search)
        except HeliumICalError as ex:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            raise ValidationError(ex)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
