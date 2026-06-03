__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.db.models import Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample
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
from helium.planner.services.eventservice import clone_event
from helium.planner.views.base import HeliumCalendarItemAPIView, CALENDAR_DATE_RANGE_PARAMETERS

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
            return user.events.select_related('user').prefetch_related(
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
        summary='List Events for the User',
        parameters=CALENDAR_DATE_RANGE_PARAMETERS,
        tags=['planner.event']
    )
    def get(self, request, *args, **kwargs):
        """
        Return all Helium Event instances for the authenticated user. `attachments` and `reminders` are nested inline.
        """
        response = super().get(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary='Create an Event',
        responses={
            201: EventExtendedSerializer
        },
        examples=[
            OpenApiExample(
                'office_hours',
                summary='Weekly office-hours event (one occurrence)',
                description=(
                    'A single Event occurrence. For recurring events, enumerate one row per '
                    'occurrence, use the bulk-import path, or clone-and-PATCH a canonical row.'
                ),
                value={
                    'title': 'Office Hours — Prof. Smith',
                    'all_day': False,
                    'show_end_time': True,
                    'start': '2026-09-23T15:00:00-07:00',
                    'end': '2026-09-23T16:30:00-07:00',
                    'priority': 30,
                    'url': 'https://example.edu/zoom/abc123',
                },
                request_only=True,
            ),
        ],
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
            return user.events.select_related('user').prefetch_related(
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

    @extend_schema(summary='Retrieve an Event')
    def get(self, request, *args, **kwargs):
        """
        Return the given Helium Event instance. `attachments` and `reminders` are nested inline.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(summary='Update an Event', responses={200: EventExtendedSerializer})
    def put(self, request, *args, **kwargs):
        """
        Update the given Helium Event instance.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Event {kwargs['pk']} updated for user {request.user.pk}")

        return Response(EventExtendedSerializer(serializer.instance).data)

    @extend_schema(summary='Partially update an Event', responses={200: EventExtendedSerializer})
    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given Helium Event instance.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Event {kwargs['pk']} patched for user {request.user.pk}")

        return Response(EventExtendedSerializer(serializer.instance).data)

    @extend_schema(
        summary='Delete an Event',
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
class EventsApiCloneView(HeliumAPIView, RetrieveModelMixin):
    serializer_class = EventExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            return self.request.user.events.all()
        else:
            return Event.objects.none()

    @extend_schema(
        summary='Clone an Event',
        request=None,
        responses={
            201: EventExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Clone the given event instance, including its reminders.
        """
        source = self.get_object()

        clone = clone_event(source)

        return Response(EventExtendedSerializer(clone).data, status=status.HTTP_201_CREATED)


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

    @extend_schema(summary='Delete all Events for the User')
    def delete_all(self, request, *args, **kwargs):
        """
        Permanently delete **every** Helium Event instance owned by the authenticated user, along with any
        notes attached to those events. This operation is irreversible and cannot be filtered or
        scoped — it affects the entire user's event history. Course-derived schedules and homework
        are not touched.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Delete associated notes first since bulk delete doesn't trigger signals
        Note.objects.filter(events__in=queryset).delete()

        queryset.delete()

        logger.info(f"All events deleted for user {request.user.pk}")

        return Response(status=status.HTTP_204_NO_CONTENT)
