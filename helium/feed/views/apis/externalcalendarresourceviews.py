__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.16.18"

import logging
from datetime import timezone, datetime

from dateutil import parser
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
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

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
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

        # TODO: Remap legacy query params, will be removed
        request.query_params._mutable = True
        if 'start__gte' in request.query_params:
            request.query_params['from'] = request.query_params.pop('start__gte')
        if 'end__lt' in request.query_params:
            request.query_params['to'] = request.query_params.pop('end__lt')

        _from = request.query_params.get('from', None)
        to = request.query_params.get('to', None)

        if _from:
            _from = parser.parse(_from[0]).astimezone(timezone.utc)
        if to:
            to = parser.parse(to[0]).astimezone(timezone.utc)
        search = request.query_params["search"].lower() if "search" in request.query_params else None

        try:
            events = icalexternalcalendarservice.calendar_to_events(external_calendar, _from, to, search)
        except HeliumICalError as ex:
            external_calendar.shown_on_calendar = False
            external_calendar.save()

            raise ValidationError(ex)

        serializer = self.get_serializer(events, many=True)

        return Response(serializer.data)
