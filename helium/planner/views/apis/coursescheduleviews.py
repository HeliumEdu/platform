__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import status
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner.filters import CourseScheduleFilter
from helium.planner.models import CourseSchedule
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.courseschedule']
)
class UserCourseSchedulesApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = CourseScheduleFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return CourseSchedule.objects.for_user(user.pk)
        else:
            return CourseSchedule.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all course schedule instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response


@extend_schema(
    tags=['planner.courseschedule']
)
class CourseGroupCourseCourseSchedulesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CourseScheduleSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filterset_class = CourseScheduleFilter

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
        },
        examples=[
            OpenApiExample(
                'mwf_lecture',
                summary='MWF lecture, 10:00-10:50 AM',
                description=(
                    '`days_of_week` is a 7-character `0`/`1` string starting Sunday. `0101010` flags '
                    'Monday, Wednesday, and Friday as meetings; the matching `<day>_start_time` and '
                    '`<day>_end_time` carry the actual times. Off-day fields are left at `00:00:00`.'
                ),
                value={
                    'days_of_week': '0101010',
                    'sun_start_time': '00:00:00',
                    'sun_end_time': '00:00:00',
                    'mon_start_time': '10:00:00',
                    'mon_end_time': '10:50:00',
                    'tue_start_time': '00:00:00',
                    'tue_end_time': '00:00:00',
                    'wed_start_time': '10:00:00',
                    'wed_end_time': '10:50:00',
                    'thu_start_time': '00:00:00',
                    'thu_end_time': '00:00:00',
                    'fri_start_time': '10:00:00',
                    'fri_end_time': '10:50:00',
                    'sat_start_time': '00:00:00',
                    'sat_end_time': '00:00:00',
                },
                request_only=True,
            ),
            OpenApiExample(
                'tr_lab',
                summary='Tu/Th lab, 1:30-3:20 PM',
                description=(
                    'A Tuesday/Thursday lab schedule. `days_of_week` is `0010100`. Tue/Thu times are '
                    'populated, all other days remain at `00:00:00`.'
                ),
                value={
                    'days_of_week': '0010100',
                    'sun_start_time': '00:00:00',
                    'sun_end_time': '00:00:00',
                    'mon_start_time': '00:00:00',
                    'mon_end_time': '00:00:00',
                    'tue_start_time': '13:30:00',
                    'tue_end_time': '15:20:00',
                    'wed_start_time': '00:00:00',
                    'wed_end_time': '00:00:00',
                    'thu_start_time': '13:30:00',
                    'thu_end_time': '15:20:00',
                    'fri_start_time': '00:00:00',
                    'fri_end_time': '00:00:00',
                    'sat_start_time': '00:00:00',
                    'sat_end_time': '00:00:00',
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """
        Create the course schedule for the given course. A course has at most one schedule — repeated calls
        on a course that already has one are rejected.

        `days_of_week` is a string of seven `0`/`1` characters starting Sunday (e.g. `0101010` for Mon/Wed/Fri).
        Each day has its own `<day>_start_time` / `<day>_end_time` pair; for each day the start must be
        on-or-before the end. Days flagged `0` in `days_of_week` are not meetings, but the time fields are still
        accepted and stored (typically left at the defaults).
        """
        response = self.create(request, *args, **kwargs)

        logger.info(
            f"CourseSchedule {response.data['id']} created in Course {kwargs['course']} for user {request.user.pk}")

        return response


@extend_schema(
    tags=['planner.courseschedule']
)
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

        logger.info(f"CourseSchedule {kwargs['pk']} updated for user {request.user.pk}")

        return response

    @extend_schema(deprecated=True, exclude=True)
    def delete(self, request, *args, **kwargs):
        """
        Delete the given course schedule instance.
        """
        return Response(
            {'detail': 'Deleting a course schedule is not allowed. Each course must have exactly one schedule.'},
            status=status.HTTP_400_BAD_REQUEST
        )
