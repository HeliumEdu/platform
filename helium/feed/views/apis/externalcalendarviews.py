import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.utils import metricutils
from helium.feed.models import ExternalCalendar
from helium.feed.permissions import IsOwner
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ExternalCalendarsApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all external calendar instances for the authenticated user.

    post:
    Create a new external calendar instance for the authenticated user.
    """
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info(
            'ExternalCalendar {} created for user {}'.format(response.data['id'], request.user.get_username()))

        metricutils.increment(request, 'action.externalcalendar.created')

        return response


class ExternalCalendarsApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given external calendar instance.

    put:
    Update the given external calendar instance.

    delete:
    Delete the given external calendar instance.
    """
    queryset = ExternalCalendar.objects.all()
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info(
            'ExternalCalendar {} update for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.externalcalendar.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'ExternalCalendar {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.externalcalendar.deleted')

        return response
