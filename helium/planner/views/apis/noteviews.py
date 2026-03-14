__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import filters
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner.filters import NoteFilter
from helium.planner.models import Note
from helium.planner.serializers.noteserializer import NoteSerializer, NoteExtendedSerializer, NoteListSerializer

logger = logging.getLogger(__name__)


@extend_schema(tags=['planner.note'])
class NotesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = NoteSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter)
    filterset_class = NoteFilter
    search_fields = ('title',)
    ordering_fields = ('title', 'created_at', 'updated_at')

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, 'swagger_fake_view', False):
            return self.request.user.notes.prefetch_related(
                'links__homework__course',
                'links__event',
                'links__resource'
            ).all()
        return Note.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return NoteListSerializer
        return self.serializer_class

    def get(self, request, *args, **kwargs):
        """
        Return a list of all Note instances for the authenticated user.
        Excludes content field to reduce payload size.
        """
        return self.list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        responses={
            201: NoteSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new Note instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"Note {response.data['id']} created for user {request.user.pk}")

        return response


@extend_schema(tags=['planner.note'])
class NotesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = NoteSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, 'swagger_fake_view', False):
            return self.request.user.notes.prefetch_related(
                'links__homework__course',
                'links__event',
                'links__resource'
            ).all()
        return Note.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return NoteExtendedSerializer
        return self.serializer_class

    def get(self, request, *args, **kwargs):
        """
        Return the given Note instance.
        """
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        """
        Update the given Note instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"Note {kwargs['pk']} updated for user {request.user.pk}")

        return response

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given Note instance.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Note {kwargs['pk']} patched for user {request.user.pk}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given Note instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Note {kwargs['pk']} deleted for user {request.user.pk}")

        return response
