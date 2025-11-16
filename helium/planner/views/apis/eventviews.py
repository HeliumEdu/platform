__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.22"

import logging
from datetime import datetime

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, status
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner.filters import EventFilter
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import EventSerializer, EventExtendedSerializer
from helium.planner.views.base import HeliumCalendarItemAPIView

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.event']
)
class EventsApiListView(HeliumCalendarItemAPIView, CreateModelMixin):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filterset_class = EventFilter
    search_fields = ('title', 'comments')
    order_fields = ('start', 'title', 'priority',)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.events.all()
        else:
            return Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
        else:
            return self.serializer_class

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
        ],
        tags=['planner.event', 'calendar.user']
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all Helium Event instances for the authenticated user. For convenience, Helium Events on a GET
        are serialized with representations of associated attachments and reminders to avoid the need for redundant API
        calls.
        """
        response = super().get(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        responses={
            201: EventSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new Helium Event instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"Event {response.data['id']} created for user {request.user.get_username()}")

        return response


@extend_schema(
    tags=['planner.event']
)
class EventsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.events.all()
        else:
            return Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
        else:
            return self.serializer_class

    def get(self, request, *args, **kwargs):
        """
        Return the given Helium Event instance. For convenience, Helium Event instances on a GET are serialized with
        representations of associated attachments and reminders to avoid the need for redundant API calls.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given Helium Event instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given Helium Event instance.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} patched for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given Helium Event instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response


@extend_schema(
    tags=['planner.event']
)
class EventsApiDeleteResourceView(ViewSet, HeliumAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.events.all()
        else:
            return Event.objects.none()

    def delete_all(self, request, *args, **kwargs):
        """
        Delete all Helium Event instances for the authenticated user.
        """
        queryset = self.filter_queryset(self.get_queryset())

        queryset.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
