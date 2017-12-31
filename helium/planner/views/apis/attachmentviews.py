import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.models import Course
from helium.planner.serializers.attachmentserializer import AttachmentSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseAttachmentsApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all attachment instances for the given course.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.attachments.filter(course_id=self.kwargs['course_id'])

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            raise NotFound('Course not found.')

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class UserAttachmentsApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all attachment instances for the authenticated user.

    post:
    Create a new attachment instance for the authenticated user.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    # TODO: in the future, refactor this (and the frontend) to only use the FileUploadParser
    parser_classes = (FormParser, MultiPartParser,)

    def get_queryset(self):
        user = self.request.user
        return user.attachments.all()

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            raise NotFound('Course not found.')

    def get_course(self, course_id):
        self.check_course_permission(self.request, course_id)

        return Course.objects.get(course_group__user_id=self.request.user.pk, id=course_id)

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        data = request.data.copy()

        response_data = {}
        errors = {}
        for upload in request.data.getlist('file[]'):
            data['title'] = upload.name
            data['attachment'] = upload

            # We're popping it off so the serializer doesn't validate it, as it will be validated later
            course_id = data['course'] if 'course' in data else None
            data.pop('course')

            serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                serializer.save(
                    course=self.get_course(course_id) if course_id else None,
                    # TODO: uncomment and create functionswhen these models exist
                    # event=self.get_event(data['event']) if 'event' in data else None,
                    # homework=self.get_homework(data['homework']) if 'homework' in data else None,
                    user=request.user,
                )

                logger.info(
                    'Attachment {} created for user {}'.format(serializer.instance.pk, request.user.get_username()))

                metricutils.increment(request, 'action.attachment.created')

                response_data.update(serializer.data)
            else:
                errors.update(serializer.errors)

        if len(errors) > 0:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        elif len(response_data) > 0:
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response({'details': 'An unknown error occurred.'}, status=status.HTTP_400_BAD_REQUEST)


class AttachmentsApiDetailView(GenericAPIView, RetrieveModelMixin, DestroyModelMixin):
    """
    get:
    Return the given attachment instance.

    delete:
    Delete the given attachment instance.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        user = self.request.user
        return user.attachments.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Attachment {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.attachment.deleted')

        return response
