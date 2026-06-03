__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import filters
from rest_framework import status
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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
                'homework__course',
                'homework__category',
                'events',
                'resources'
            ).all()
        return Note.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            # Include content field when explicitly requested
            if self.request.query_params.get('include_content') == 'true':
                return NoteExtendedSerializer
            return NoteListSerializer
        return self.serializer_class

    @extend_schema(
        summary='List Notes for the User',
        parameters=[
            OpenApiParameter(
                name='include_content',
                type=bool,
                description='By default the `content` field is omitted from list responses to keep them light. '
                            'Pass `true` to include the full [Quill Delta](https://quilljs.com/docs/delta/) JSON of each note.',
            ),
        ],
    )
    def get(self, request, *args, **kwargs):
        """
        Return all notes for the authenticated user.
        """
        return self.list(request, *args, **kwargs)

    @extend_schema(
        summary='Create a Note',
        responses={
            201: NoteExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a note for the authenticated user.

        To link a note, pass exactly one of `homework`, `event`, or `resource` (a `Material`); giving more than one type,
        more than one item of the same type, or an entity that already has a note returns a 400.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(user=request.user)

        logger.info(f"Note {instance.id} created for user {request.user.pk}")

        return Response(NoteExtendedSerializer(instance).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['planner.note'])
class NotesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = NoteSerializer
    permission_classes = (IsAuthenticated, IsOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, 'swagger_fake_view', False):
            return self.request.user.notes.prefetch_related(
                'homework__course',
                'homework__category',
                'events',
                'resources'
            ).all()
        return Note.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return NoteExtendedSerializer
        return self.serializer_class

    @extend_schema(summary='Retrieve a Note')
    def get(self, request, *args, **kwargs):
        """
        Return the given note instance.
        """
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(summary='Update a Note', responses={
        200: NoteExtendedSerializer,
        204: OpenApiResponse(description='Returned in place of the updated note when a linked note has its '
                                          'content cleared and is therefore deleted (see endpoint description).'),
    })
    def put(self, request, *args, **kwargs):
        """
        Update the given note.

        If `content` is cleared while the note is linked to an entity, the note is deleted and a 204 is
        returned in place of the updated note.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.should_delete_on_empty_content(instance, serializer.validated_data):
            instance.delete()
            logger.info(f"Note {kwargs['pk']} deleted (content cleared) for user {request.user.pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        result = serializer.save()
        logger.info(f"Note {kwargs['pk']} updated for user {request.user.pk}")
        return Response(NoteExtendedSerializer(result).data)

    @extend_schema(summary='Partially update a Note', responses={
        200: NoteExtendedSerializer,
        204: OpenApiResponse(description='Returned in place of the updated note when a linked note has its '
                                          'content cleared and is therefore deleted (see endpoint description).'),
    })
    def patch(self, request, *args, **kwargs):
        """
        Partially update the given note.

        If `content` is given and cleared while the note is linked to an entity, the note is deleted and a
        204 is returned in place of the updated note.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        if serializer.should_delete_on_empty_content(instance, serializer.validated_data):
            instance.delete()
            logger.info(f"Note {kwargs['pk']} deleted (content cleared) for user {request.user.pk}")
            return Response(status=status.HTTP_204_NO_CONTENT)

        result = serializer.save()
        logger.info(f"Note {kwargs['pk']} patched for user {request.user.pk}")
        return Response(NoteExtendedSerializer(result).data)

    @extend_schema(summary='Delete a Note')
    def delete(self, request, *args, **kwargs):
        """
        Delete the given note instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Note {kwargs['pk']} deleted for user {request.user.pk}")

        return response
