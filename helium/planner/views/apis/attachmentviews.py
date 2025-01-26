__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.8.2"

import logging

from rest_framework import status
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner import permissions
from helium.planner.models import Attachment
from helium.planner.schemas import AttachmentListSchema, AttachmentDetailSchema
from helium.planner.serializers.attachmentserializer import AttachmentSerializer

logger = logging.getLogger(__name__)


class AttachmentsApiListView(HeliumAPIView, ListModelMixin):
    """
    get:
    Return a list of all attachment instances for the authenticated user. To download the attachment, follow the link
    contained in the `attachment` field of an instance, which will direct you to attached media URL.

    post:
    Create new attachment instances and upload the associated files for the authenticated user. Multiple files can be
    passed in the `file[]` field, but note that even if only one file is created, the response will still contain a
    list.

    The `title` attribute is set dynamically by the `filename` field passed for each file to be uploaded.

    The maximum file size for each upload is 10M.

    At least one of `course`, `event`, or `homework` must be given.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = AttachmentSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields = ('course', 'event', 'homework',)
    schema = AttachmentListSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.attachments.all()
        else:
            return Attachment.objects.none()

    def options(self, request, *args, **kwargs):  # pragma: no cover
        """
        Manually specifying the POST parameters to show when OPTIONS is called, as they don't directly map to the
        serializer (which is used for GET and other operations).
        """
        response = super().options(request, *args, **kwargs)

        self.schema.modify_options_response(response)

        return response

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def post(self, request, *args, **kwargs):
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])

        response_data = []
        errors = []
        for upload in request.data.getlist('file[]'):
            request.data['title'] = upload.name
            request.data['attachment'] = upload

            serializer = self.get_serializer(data=request.data)

            if serializer.is_valid():
                serializer.save(user=request.user)

                logger.info(
                    f'Attachment {serializer.instance.pk} created for user {request.user.get_username()}')

                response_data.append(serializer.data)
            else:
                errors.append(serializer.errors)

        if len(errors) > 0:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)
        elif len(response_data) > 0:
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            return Response({'details': 'An unknown error occurred.'}, status=status.HTTP_400_BAD_REQUEST)


class AttachmentsApiDetailView(HeliumAPIView, RetrieveModelMixin, DestroyModelMixin):
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
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.attachments.all()
        else:
            return Attachment.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Attachment {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
