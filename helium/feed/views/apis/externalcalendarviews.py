__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.feed.filters import ExternalCalendarFilter
from helium.feed.models import ExternalCalendar
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.externalcalendar']
)
class ExternalCalendarsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ExternalCalendarFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    @extend_schema(summary='List ExternalCalendars for the User')
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary='Register an ExternalCalendar',
        responses={
            201: ExternalCalendarSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new external calendar instance for the authenticated user.

        The server will fetch `url` and validate the response is a valid iCal feed, and if not a
        400 is returned.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {response.data['id']} created for user {request.user.get_username()}")

        return response


@extend_schema(
    tags=['feed.externalcalendar']
)
class ExternalCalendarsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    @extend_schema(summary='Retrieve an ExternalCalendar')
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(summary='Update an ExternalCalendar')
    def put(self, request, *args, **kwargs):
        """
        Update the given external calendar instance.

        The server will fetch `url` and validate the response is a valid iCal feed, and if not a
        400 is returned.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    @extend_schema(summary='Partially update an ExternalCalendar')
    def patch(self, request, *args, **kwargs):
        """
        Partially update the given external calendar instance.

        If `url`` is given, the server will fetch it and validate the response is a valid iCal feed, and if not a
        400 is returned.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} partially updated for user {request.user.get_username()}")

        return response

    @extend_schema(
        summary='Delete an ExternalCalendar',
        tags=['feed.externalcalendar']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given external calendar instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
