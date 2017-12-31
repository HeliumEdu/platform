import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.utils import metricutils
from helium.planner.models import Course, Attachment
from helium.planner.permissions import IsOwner
from helium.planner.serializers.attachmentserializer import AttachmentSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseAttachmentsApiListView(GenericAPIView):
    """
    get:
    Return a list of all attachment instances for the given course.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id).exists():
            raise NotFound('Course not found.')
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get(self, request, course_id, format=None):
        self.check_course_permission(request, course_id)

        attachments = Attachment.objects.filter(course_id=course_id)

        serializer = self.get_serializer(attachments, many=True)

        return Response(serializer.data)


class UserAttachmentsApiListView(GenericAPIView):
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

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id).exists():
            raise NotFound('Course not found.')
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get_course(self, course_id):
        self.check_course_permission(self.request, course_id)

        return Course.objects.get(course_group__user_id=self.request.user.pk, id=course_id)

    def get(self, request, *args, **kwargs):
        attachments = Attachment.objects.filter(user_id=request.user.pk)

        serializer = self.get_serializer(attachments, many=True)

        return Response(serializer.data)

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


class AttachmentsApiDetailView(GenericAPIView):
    """
    get:
    Return the given attachment instance.

    delete:
    Delete the given attachment instance.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_object(self, request, pk):
        try:
            return Attachment.objects.get(pk=pk)
        except Attachment.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        attachment = self.get_object(request, pk)
        self.check_object_permissions(request, attachment)

        serializer = self.get_serializer(attachment)

        return Response(serializer.data)

    def delete(self, request, pk, format=None):
        attachment = self.get_object(request, pk)
        self.check_object_permissions(request, attachment)

        attachment.delete()

        logger.info('Attachment {} deleted for user {}'.format(pk, request.user.get_username()))

        metricutils.increment(request, 'action.attachment.deleted')

        return Response(status=status.HTTP_204_NO_CONTENT)
