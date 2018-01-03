import logging

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.serializers.attachmentserializer import AttachmentSerializer
from helium.planner.views.apis.schemas.attachmentschemas import AttachmentDetailSchema, AttachmentListSchema
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

    def get(self, request, *args, **kwargs):
        permissions.check_course_group_permission(request, kwargs['course_group'])
        permissions.check_course_permission(request, kwargs['course'])

        response = self.list(request, *args, **kwargs)

        return response


class UserAttachmentsApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all attachment instances for the authenticated user. To download the attachment, follow the link
    contained in the `attachment` field of an instance, which will direct you to attached media URL.

    post:
    Create new attachment instances and upload the associated files for the authenticated user. Multiple files can be
    passed in the `file[]` field, but note that even if only one file is created, the response will still contain a
    list.

    The `title` attribute is set dynamically by the `filename` field passed for each file to be uploaded.

    At least one of `course`, `event`, or `homework` must be given.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    schema = AttachmentListSchema()

    def get_queryset(self):
        user = self.request.user
        return user.attachments.all()

    def options(self, request, *args, **kwargs):  # pragma: no cover
        """
        Manually specifying the POST parameters to show when OPTIONS is called, as they don't directly map to the
        serializer (which is used for GET and other operations).
        """
        response = super(UserAttachmentsApiListView, self).options(request, args, kwargs)

        self.schema.modify_options_response(response)

        return response

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        data = request.data.copy()

        if 'course' in request.data:
            permissions.check_course_permission(request, request.data['course'])
        if 'event' in request.data:
            permissions.check_event_permission(request, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request, request.data['homework'])

        response_data = []
        errors = []
        for upload in request.data.getlist('file[]'):
            data['title'] = upload.name
            data['attachment'] = upload

            serializer = self.get_serializer(data=data)

            if serializer.is_valid():
                serializer.save(user=request.user)

                logger.info(
                    'Attachment {} created for user {}'.format(serializer.instance.pk, request.user.get_username()))

                metricutils.increment(request, 'action.attachment.created')

                response_data.append(serializer.data)
            else:
                errors.append(serializer.errors)

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
    schema = AttachmentDetailSchema()

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
