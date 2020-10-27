import logging

from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.schemas import ExternalCalendarIDSchema
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


class ExternalCalendarsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all external calendar instances for the authenticated user.

    post:
    Create a new external calendar instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated,)
    filter_fields = ('shown_on_calendar',)

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {response.data['id']} created for user {request.user.get_username()}")

        return response


class ExternalCalendarsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given external calendar instance.

    put:
    Update the given external calendar instance.

    delete:
    Delete the given external calendar instance.
    """
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ExternalCalendarIDSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.external_calendars.all()
        else:
            return ExternalCalendar.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} update for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"ExternalCalendar {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
