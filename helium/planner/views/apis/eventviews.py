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
from helium.common.search import HeliumSearchFilter
from helium.common.views.base import IF_MATCH_PARAMETER, HeliumAPIView, PreconditionMixin
from helium.planner.filters import EventFilter
from helium.planner.models import Event, Reminder, Note
from helium.planner.serializers.eventserializer import EventSerializer, EventExtendedSerializer
from helium.planner.services.eventservice import clone_event
from helium.planner.views.base import HeliumCalendarItemAPIView, CALENDAR_DATE_RANGE_PARAMETERS, SCOPE_ALL, \
    SCOPE_THIS, OCCURRENCE_START_PARAMETER, RepeatingItemDetailMixin, occurrence_start_param, scope_parameter

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.event']
)
class EventsApiListView(HeliumCalendarItemAPIView, CreateModelMixin):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, HeliumSearchFilter,)
    filterset_class = EventFilter
    search_fields = ('title',)
    search_description = 'Search by title.'
    ordering_fields = ('start', 'title', 'priority',)

    def get_queryset(self):
        if self.has_request_user():
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
                summary='Weekly office-hours event',
                description='Office hours every Wednesday, repeating from `start`.',
                value={
                    'title': 'Office Hours — Prof. Smith',
                    'all_day': False,
                    'show_end_time': True,
                    'start': '2026-09-23T15:00:00-07:00',
                    'end': '2026-09-23T16:30:00-07:00',
                    'priority': 30,
                    'url': 'https://example.edu/zoom/abc123',
                    'recurrence_rule': 'FREQ=WEEKLY;BYDAY=WE',
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
class EventsApiDetailView(RepeatingItemDetailMixin, PreconditionMixin, HeliumAPIView, RetrieveModelMixin,
                          UpdateModelMixin, DestroyModelMixin):
    serializer_class = EventSerializer
    precondition_serializer_class = EventExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if self.has_request_user():
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

    @extend_schema(summary='Update an Event', parameters=[IF_MATCH_PARAMETER],
                   responses={200: EventExtendedSerializer})
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

    @extend_schema(
        summary='Partially update an Event',
        parameters=[
            IF_MATCH_PARAMETER,
            scope_parameter(SCOPE_ALL, '`all` updates the Event, and a repeating Event\'s whole series. `this` '
                                       'makes the occurrence at `occurrence_start` its own Event, with the '
                                       'series\' reminders, and leaves it out of the series, which keeps its note '
                                       'and attachments.'),
            OCCURRENCE_START_PARAMETER,
        ],
        responses={200: EventExtendedSerializer},
    )
    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given Helium Event instance. With `occurrence_start`, `start` / `end`
        are that occurrence's new times, and the whole series moves with it. With `scope=this`, the response is the
        new Event.
        """
        return self.update_in_scope(request, EventExtendedSerializer)

    @extend_schema(
        summary='Delete an Event',
        parameters=[
            IF_MATCH_PARAMETER,
            scope_parameter(SCOPE_ALL, '`all` deletes the Event, and a repeating Event\'s whole series. `this` '
                                       'deletes only the occurrence at `occurrence_start`; deleting the last one '
                                       'deletes the series.'),
            OCCURRENCE_START_PARAMETER,
        ],
        tags=['planner.event']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given Helium Event instance.
        """
        return self.destroy_in_scope(request, *args, **kwargs)


@extend_schema(
    tags=['planner.event']
)
class EventsApiCloneView(HeliumAPIView, RetrieveModelMixin):
    serializer_class = EventExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if self.has_request_user():
            return self.request.user.events.all()
        else:
            return Event.objects.none()

    @extend_schema(
        summary='Clone an Event',
        request=None,
        parameters=[OCCURRENCE_START_PARAMETER],
        responses={
            201: EventExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Clone the given event instance, including its reminders. A repeating event is cloned at the occurrence at
        `occurrence_start`, or at its `start` when omitted, and the clone doesn't repeat.
        """
        source = self.get_object()

        clone = clone_event(source, occurrence_start_param(request, required=False))

        return Response(EventExtendedSerializer(clone).data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['planner.event']
)
class EventsApiDeleteResourceView(ViewSet, HeliumAPIView):
    serializer_class = EventSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if self.has_request_user():
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

        Note.objects.filter(events__in=queryset).delete()

        queryset.delete()

        logger.info(f"All events deleted for user {request.user.pk}")

        return Response(status=status.HTTP_204_NO_CONTENT)
