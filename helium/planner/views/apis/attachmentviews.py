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
from helium.planner.views.apis.schemas.attachmentschemas import AttachmentIDSchema, AttachmentListSchema
from helium.planner.views.apis.schemas.courseschemas import SubCourseListSchema

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
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return user.attachments.filter(course_id=self.kwargs['course'])

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            raise NotFound('Course not found.')

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class UserAttachmentsApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all attachment instances for the authenticated user. To download the attachment, follow the link
    contained in the `attachment` field of an instance, which will direct you to attached media URL.

    post:
    Create a new attachment instance and upload the associated file for the authenticated user. If multiple files are
    given in `file[]`, multiple files will be created.

    The `title` attribute is set dynamically by the `filename` field passed for each file to be uploaded.

    At least one of `course`, `event`, or `homework` must be given.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    # TODO: in the future, refactor this (and the frontend) to only use the FileUploadParser
    parser_classes = (FormParser, MultiPartParser,)
    schema = AttachmentListSchema()

    def get_queryset(self):
        user = self.request.user
        return user.attachments.all()

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            raise NotFound('Course not found.')

    def check_event_permission(self, request, course_id):
        pass
        # TODO: uncomment and when these models exist
        # if not Event.objects.filter(pk=course_id, user_id=request.user.pk).exists():
        #     raise NotFound('Event not found.')

    def check_homework_permission(self, request, course_id):
        pass
        # TODO: uncomment and when these models exist
        # if not Homework.objects.filter(pk=course_id, course__course_group__user_id=request.user.pk).exists():
        #     raise NotFound('Homework not found.')

    def options(self, request, *args, **kwargs):
        """
        Manually specifying the POST parameters to show when OPTIONS is called, as they don't directly map to the
        serializer (which is used for GET and other operations).
        """
        response = super(UserAttachmentsApiListView, self).options(request, args, kwargs)

        response.data['actions']['POST'].pop('id')
        response.data['actions']['POST'].pop('title')
        response.data['actions']['POST'].pop('attachment')
        response.data['actions']['POST'].pop('size')

        response.data['actions']['POST']['file[]'] = {
            "type": "file upload",
            "required": True,
            "read_only": False,
            "label": "Files",
            "help_text": "A multipart list of files to upload."
        }

        return response

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

            if 'course' in data:
                self.check_course_permission(request, data['course'])
            if 'event' in data:
                self.check_event_permission(request, data['event'])
            if 'homework' in data:
                self.check_homework_permission(request, data['homework'])

            serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                serializer.save(user=request.user)

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
    Return the given attachment instance. To download the attachment, follow the link contained in the `attachment`
    field of an instance, which will direct you to attached media URL.

    delete:
    Delete the given attachment instance.
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = AttachmentIDSchema()

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
