import logging

from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.filters import CourseGroupFilter
from helium.planner.models import CourseGroup
from helium.planner.schemas import CourseGroupDetailSchema
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class CourseGroupsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all course group instances for the authenticated user.

    post:
    Create a new course group instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated,)
    filter_class = CourseGroupFilter

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.course_groups.all()
        else:
            CourseGroup.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('CourseGroup {} created for user {}'.format(response.data['id'], request.user.get_username()))

        return response


class CourseGroupsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
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
    schema = CourseGroupDetailSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return user.course_groups.all()
        else:
            CourseGroup.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('CourseGroup {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('CourseGroup {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response
