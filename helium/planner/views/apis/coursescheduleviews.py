import logging

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.models import CourseSchedule
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.schemas import SubCourseListSchema, CourseScheduleDetailSchema
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2021, Helium Edu"
__version__ = "1.4.46"

logger = logging.getLogger(__name__)


class CourseGroupCourseCourseSchedulesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all course schedule instances for the given course.

    post:
    Create a new course schedule instance for the given course.
    """
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    schema = SubCourseListSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return CourseSchedule.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            CourseSchedule.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('CourseSchedule {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                                request.user.get_username()))

        return response


class CourseGroupCourseCourseSchedulesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin,
                                                    DestroyModelMixin):
    """
    get:
    Return the given course schedule instance.

    put:
    Update the given course schedule instance.

    delete:
    Delete the given course schedule instance.
    """
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)
    schema = CourseScheduleDetailSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return CourseSchedule.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            CourseSchedule.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info(f"CourseSchedule {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'CourseSchedule {} deleted from Course {} for user {}'.format(kwargs['pk'], kwargs['course'],
                                                                          request.user.get_username()))

        return response
