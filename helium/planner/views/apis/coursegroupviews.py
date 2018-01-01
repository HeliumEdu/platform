import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.views.apis.schemas.attachmentschemas import AttachmentIDSchema
from helium.planner.views.apis.schemas.coursegroupschemas import CourseGroupIDSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupsApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all course group instances for the authenticated user.

    post:
    Create a new course group instance for the authenticated user.
    """
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.course_groups.all()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('CourseGroup {} created for user {}'.format(response.data['id'], request.user.get_username()))

        metricutils.increment(request, 'action.coursegroup.created')

        return response


class CourseGroupsApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given course group instance.

    put:
    Update the given course group instance.

    delete:
    Delete the given course group instance.
    """
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = CourseGroupIDSchema()

    def get_queryset(self):
        user = self.request.user
        return user.course_groups.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('CourseGroup {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.coursegroup.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('CourseGroup {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.coursegroup.deleted')

        return response
