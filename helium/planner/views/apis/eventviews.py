__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import datetime

from django.db.models import Prefetch
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
from helium.planner.models import Event, Reminder, Note
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
            return user.events.all().prefetch_related(
                'attachments',
                'notes_set',
                Prefetch('reminders', queryset=Reminder.objects.select_related('homework', 'event'))
            )
        else:
            return Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
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
            201: EventExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new Helium Event instance for the authenticated user.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return extended serializer with note field
        instance = serializer.instance
        response_serializer = EventExtendedSerializer(instance)

        logger.info(f"Event {instance.pk} created for user {request.user.pk}")

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['planner.event']
)
class EventsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.events.all().prefetch_related(
                'attachments',
                'notes_set',
                Prefetch('reminders', queryset=Reminder.objects.select_related('homework', 'event'))
            )
        else:
            return Event.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return EventExtendedSerializer
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
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Event {kwargs['pk']} updated for user {request.user.pk}")

        # Return extended serializer with note field
        return Response(EventExtendedSerializer(serializer.instance).data)

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given Helium Event instance.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Event {kwargs['pk']} patched for user {request.user.pk}")

        # Return extended serializer with note field
        return Response(EventExtendedSerializer(serializer.instance).data)

    @extend_schema(
        tags=['planner.event']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given Helium Event instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} deleted for user {request.user.pk}")

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

        # Delete associated notes first since bulk delete doesn't trigger signals
        Note.objects.filter(events__in=queryset).delete()

        queryset.delete()

        logger.info(f"All events deleted for user {request.user.pk}")

        return Response(status=status.HTTP_204_NO_CONTENT)
