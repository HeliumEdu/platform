__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.planner.models import Event
from helium.feed.services.icalexternalcalendarservice import HeliumICalError
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.views.base import HeliumCalendarItemAPIView, CALENDAR_DATE_RANGE_PARAMETERS, \
    _parse_date_param_to_utc

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.externalcalendar.event']
)
class UserExternalCalendarAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Event.objects.none()
        return Event.objects.none()

    @extend_schema(
        parameters=[
            *CALENDAR_DATE_RANGE_PARAMETERS,
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return all external calendar events the user has shown on their calendar, flattened across every
        subscribed external calendar.

        The `id` on each event is sequential within this response only — not stable across requests, and not
        an `Event` primary key. Do not persist these IDs client-side.

        Side effect: if a subscribed external calendar fails to fetch or parse periodically, it is auto-disabled
        (`shown_on_calendar` flipped to `false`). PATCH it back to `true` once the upstream feed is fixed.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        user = request.user
        external_calendars = (ExternalCalendar.objects
                              .for_user(user.pk)
                              .select_related('user', 'user__settings'))
        if 'shown_on_calendar' in request.query_params:
            external_calendars = external_calendars.filter(shown_on_calendar=request.query_params['shown_on_calendar'].lower() == 'true')

        user_tz_name = user.settings.time_zone
        _from = _parse_date_param_to_utc(request.query_params["from"], user_tz_name) \
            if "from" in request.query_params else None
        to = _parse_date_param_to_utc(request.query_params["to"], user_tz_name) \
            if "to" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        events = []
        for external_calendar in external_calendars:
            try:
                events += icalexternalcalendarservice.calendar_to_events(external_calendar, _from, to, search)
            except HeliumICalError:
                external_calendar.shown_on_calendar = False
                external_calendar.save()
                logger.warning(f"External Calendar {external_calendar.pk} is not a valid ICAL feed, disabled.")

        # Re-assign sequential IDs to ensure uniqueness across all calendars.
        # TODO: Once the legacy frontend (frontend-legacy) is shut down, replace this with
        # stable IDs derived from each event's ICS UID so the frontend can reliably
        # deduplicate the same event returned by different date-range queries. The new
        # frontend already works around this limitation with content-based deduplication.
        for i, event in enumerate(events):
            event.id = i

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)


@extend_schema(
    tags=['feed.externalcalendar.event']
)
class ExternalCalendarAsEventsListView(HeliumCalendarItemAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Event.objects.none()
        return Event.objects.none()

    @extend_schema(
        operation_id='feed_externalcalendar_events_list',
        parameters=[
            *CALENDAR_DATE_RANGE_PARAMETERS,
            OpenApiParameter(name='search', description='A search term.', type=str),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return the events from a single subscribed external calendar's iCal feed.

        The `id` on each event is sequential within this response only — not stable across requests, and not
        an `Event` primary key. Do not persist these IDs client-side.

        If the upstream iCal fetch fails or the feed cannot be parsed, the request fails AND, as a side
        effect, the external calendar is auto-disabled (`shown_on_calendar` flipped to `false`). PATCH it
        back to `true` once the upstream feed is fixed.
        """
        return super().get(request, *args, **kwargs)

    def list(self, request, *arg, **kwargs):
        try:
            external_calendar = (ExternalCalendar.objects
                                 .for_user(request.user.id)
                                 .select_related('user', 'user__settings')
                                 .get(pk=self.kwargs['pk']))
        except ExternalCalendar.DoesNotExist:
            raise NotFound()

        user_tz_name = external_calendar.user.settings.time_zone
        _from = _parse_date_param_to_utc(request.query_params["from"], user_tz_name) \
            if "from" in request.query_params else None
        to = _parse_date_param_to_utc(request.query_params["to"], user_tz_name) \
            if "to" in request.query_params else None
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        try:
            events = icalexternalcalendarservice.calendar_to_events(external_calendar, _from, to, search)
        except HeliumICalError:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            logger.warning(f"An error occurred while trying to fetch external calendar {external_calendar.pk}", exc_info=True)

            raise ValidationError(f"External Calendar {external_calendar.pk} is not a valid ICAL feed, disabled.")

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
