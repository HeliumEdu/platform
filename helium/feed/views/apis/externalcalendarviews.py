__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.19"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['feed.externalcalendar']
)
class ExternalCalendarsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ('shown_on_calendar',)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all external calendar instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        responses={
            201: ExternalCalendarSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new external calendar instance for the authenticated user.
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

    def get(self, request, *args, **kwargs):
        """
        Return the given external calendar instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given external calendar instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given external calendar instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
