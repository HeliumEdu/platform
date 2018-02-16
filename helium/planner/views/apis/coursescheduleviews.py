import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.models import CourseSchedule
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.schemas import SubCourseListSchema, CourseScheduleDetailSchema
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class CourseGroupCourseCourseSchedulesApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
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

        metricutils.increment('action.courseschedule.created', request)

        return response


class CourseGroupCourseCourseSchedulesApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin,
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
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('CourseSchedule {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.courseschedule.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'CourseSchedule {} deleted from Course {} for user {}'.format(kwargs['pk'], kwargs['course'],
                                                                          request.user.get_username()))

        metricutils.increment('action.courseschedule.deleted', request)

        return response
