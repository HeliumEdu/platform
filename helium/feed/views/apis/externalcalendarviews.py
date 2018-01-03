import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import CreateModelMixin, ListModelMixin, UpdateModelMixin, RetrieveModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.feed.views.apis.schemas.externalcalendarschemas import ExternalCalendarIDSchema

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

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

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
    serializer_class = ExternalCalendarSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ExternalCalendarIDSchema()

    def get_queryset(self):
        user = self.request.user
        return user.external_calendars.all()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

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
