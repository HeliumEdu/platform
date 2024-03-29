__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

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
            f"Course {response.data['id']} created in CourseGroup {kwargs['course_group']} for user {self.request.user.get_username()}")

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

        logger.info(
            f"Course {kwargs['pk']} deleted from CourseGroup {kwargs['course_group']} for user {request.user.get_username()}")

        return response
