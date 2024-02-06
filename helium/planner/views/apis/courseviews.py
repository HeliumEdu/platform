import logging

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import CourseFilter
from helium.planner.models import Course
from helium.planner.permissions import IsCourseGroupOwner
from helium.planner.schemas import SubCourseGroupListSchema, CourseDetailSchema
from helium.planner.serializers.courseserializer import CourseSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2021, Helium Edu"
__version__ = "1.4.46"

logger = logging.getLogger(__name__)


class UserCoursesApiListView(HeliumAPIView, ListModelMixin):
    """
    get:
    Return a list of all course instances for the authenticated user, including course schedule details.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = CourseFilter

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Course.objects.for_user(user.pk)
        else:
            Course.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCoursesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all course instances, including course schedule details, for the given course group.

    post:
    Create a new course instance for the given course group.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner)
    filterset_class = CourseFilter
    schema = SubCourseGroupListSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Course.objects.for_user(user.pk).for_course_group(self.kwargs['course_group'])
        else:
            return Course.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer, *args, **kwargs):
        serializer.save(course_group_id=self.kwargs['course_group'])

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info(
            'Course {} created in CourseGroup {} for user {}'.format(response.data['id'], kwargs['course_group'],
                                                                     self.request.user.get_username()))

        return response


class CourseGroupCoursesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given course instance, including course schedule details.

    put:
    Update the given course instance.

    delete:
    Delete the given course instance.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner)
    schema = CourseDetailSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Course.objects.for_user(user.pk).for_course_group(self.kwargs['course_group'])
        else:
            Course.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        if 'course_group' in request.data:
            permissions.check_course_group_permission(request.user.pk, request.data['course_group'])

        response = self.update(request, *args, **kwargs)

        logger.info(f"Course {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Course {} deleted from CourseGroup {} for user {}'.format(kwargs['pk'], kwargs['course_group'],
                                                                               request.user.get_username()))

        return response
