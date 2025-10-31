__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.21"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.models import CourseSchedule, Course
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

logger = logging.getLogger(__name__)


class CourseGroupCourseCourseSchedulesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return CourseSchedule.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return CourseSchedule.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get(self, request, *args, **kwargs):
        """
        Return a list of all course schedule instances for the given course.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    @extend_schema(
        responses={
            201: CourseScheduleSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new course schedule instance for the given course.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(
            f"CourseSchedule {response.data['id']} created in Course {kwargs['course']} for user {request.user.get_username()}")

        return response


class CourseGroupCourseCourseSchedulesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin,
                                                    DestroyModelMixin):
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return CourseSchedule.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return CourseSchedule.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given course schedule instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given course schedule instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"CourseSchedule {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given course schedule instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"CourseSchedule {kwargs['pk']} deleted from Course {kwargs['course']} for user {request.user.get_username()}")

        return response
