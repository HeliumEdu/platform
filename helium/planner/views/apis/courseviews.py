import logging

from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course
from helium.planner.serializers.courseserializer import CourseSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserCoursesApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all course instances for the authenticated user.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseGroupCoursesApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all course instances for the given course group.

    post:
    Create a new course instance for the given course group.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(course_group_id=self.kwargs['course_group_id'],
                                     course_group__user_id=user.pk)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            raise NotFound('CourseGroup not found.')

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.check_course_group_permission(request, kwargs['course_group_id'])

        response = self.create(request, *args, **kwargs)

        logger.info(
            'Course {} created in CourseGroup {} for user {}'.format(response.data['id'], kwargs['course_group_id'],
                                                                     self.request.user.get_username()))

        metricutils.increment(request, 'action.course.created')

        return response


class CourseGroupCoursesApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given course instance.

    put:
    Update the given course instance.

    delete:
    Delete the given course instance.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            raise NotFound('CourseGroup not found.')

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(course_group_id=self.kwargs['course_group_id'], course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if 'course_group' in request.data:
            self.check_course_group_permission(request, request.data['course_group'])

        response = self.update(request, *args, **kwargs)

        logger.info('Course {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.course.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Course {} deleted from CourseGroup {} for user {}'.format(kwargs['pk'], kwargs['course_group_id'],
                                                                               request.user.get_username()))

        metricutils.increment(request, 'action.course.deleted')

        return response
