import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.filters import EventFilter
from helium.planner.models import Event
from helium.planner.schemas import EventDetailSchema
from helium.planner.serializers.eventserializer import EventSerializer, EventExtendedSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class EventsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all event instances for the authenticated user. For convenience, event instances on a GET are
    serialized with representations of associated attachments and reminders to avoid the need for redundant API calls.

    post:
    Create a new event instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filter_class = EventFilter
    search_fields = ('title',)
    order_fields = ('title', 'start', 'priority',)

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.events.all()
        else:
            Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
        else:
            return self.serializer_class

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('Event {} created for user {}'.format(response.data['id'], request.user.get_username()))

        return response


class EventsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given event instance. For convenience, event instances on a GET are serialized with representations of
    associated attachments and reminders to avoid the need for redundant API calls.

    put:
    Update the given event instance.

    patch:
    Update only the given attributes of the given event instance.

    delete:
    Delete the given event instance.
    """
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = EventDetailSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.events.all()
        else:
            Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
        else:
            return self.serializer_class

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('Event {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)

        logger.info('Event {} patched for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Event {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response
