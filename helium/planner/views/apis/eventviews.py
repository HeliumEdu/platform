import logging

from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.filters import BaseCalendarFilter
from helium.planner.schemas import EventDetailSchema
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class EventsApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all event instances for the authenticated user.

    post:
    Create a new event instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filter_class = BaseCalendarFilter
    search_fields = ('title',)
    order_fields = ('title', 'start', 'priority',)

    def get_queryset(self):
        user = self.request.user
        return user.events.all()

    def get(self, request, *args, **kwargs):
        timezone.activate(request.user.settings.time_zone)

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        timezone.activate(request.user.settings.time_zone)

        response = self.create(request, *args, **kwargs)

        logger.info('Event {} created for user {}'.format(response.data['id'], request.user.get_username()))

        metricutils.increment('action.event.created', request)

        return response


class EventsApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given event instance.

    put:
    Update the given event instance.

    delete:
    Delete the given event instance.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = EventDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return user.events.all()

    def get(self, request, *args, **kwargs):
        timezone.activate(request.user.settings.time_zone)

        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        timezone.activate(request.user.settings.time_zone)

        response = self.partial_update(request, *args, **kwargs)

        logger.info('Event {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.event.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Event {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.event.deleted', request)

        return response
