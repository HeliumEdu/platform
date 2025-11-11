__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.12.2"

import logging
from datetime import datetime, timezone

from dateutil import parser
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.filters import EventFilter
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import EventSerializer, EventExtendedSerializer

logger = logging.getLogger(__name__)


class EventsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
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

    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        query_params = self.request.query_params.copy()

        # TODO: Remap legacy query params, will be removed
        if 'start__gte' in query_params:
            query_params['from'] = query_params.pop('start__gte')
        if 'end__lt' in query_params:
            query_params['to'] = query_params.pop('end__lt')

        _from = query_params.get('from', None)
        to = query_params.get('to', None)
        if _from and to:
            _from = parser.parse(_from[0]).astimezone(timezone.utc)
            to = parser.parse(to[0]).astimezone(timezone.utc)
            queryset = queryset.filter(Q(start__range=(_from, to)) |
                                       Q(end__range=(_from, to)))

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all event instances for the authenticated user. For convenience, event instances on a GET are
        serialized with representations of associated attachments and reminders to avoid the need for redundant API
        calls.
        """
        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        response = self.list(request, *args, **kwargs)

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
        Create a new event instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"Event {response.data['id']} created for user {request.user.get_username()}")

        return response


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
        Return the given event instance. For convenience, event instances on a GET are serialized with representations of
        associated attachments and reminders to avoid the need for redundant API calls.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given event instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given event instance.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} patched for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given event instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Event {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response


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
        Delete all events for the authenticated user.
        """
        queryset = self.filter_queryset(self.get_queryset())

        queryset.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
