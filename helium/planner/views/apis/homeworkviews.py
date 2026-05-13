__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import filters, status
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import HomeworkFilter
from helium.planner.models import Homework
from helium.planner.permissions import IsCourseGroupOwner, IsCourseOwner
from helium.planner.serializers.homeworkserializer import HomeworkSerializer, HomeworkExtendedSerializer
from helium.planner.services.homeworkservice import clone_homework
from helium.planner.views.base import HeliumCalendarItemAPIView, CALENDAR_DATE_RANGE_PARAMETERS

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.homework', 'calendar.user']
)
class UserHomeworkApiListView(HeliumCalendarItemAPIView):
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filterset_class = HomeworkFilter
    search_fields = ('title', 'comments', 'category__title', 'course__title',)
    order_fields = ('start', 'title', 'completed', 'priority', 'category__title', 'course__title',)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'materials', 'notes_set')
        else:
            return Homework.objects.none()

    @extend_schema(parameters=CALENDAR_DATE_RANGE_PARAMETERS)
    def get(self, request, *args, **kwargs):
        """
        Return a list of all homework instances for the authenticated user. For convenience, homework instances on a
        GET are serialized with representations of associated attachments and reminders to avoid the need for redundant
        API calls.
        """
        response = super().get(request, *args, **kwargs)

        return response


@extend_schema(
    tags=['planner.homework']
)
class CourseGroupCourseHomeworkApiListView(HeliumCalendarItemAPIView, CreateModelMixin):
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filterset_class = HomeworkFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course']).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'materials', 'notes_set')
        else:
            return Homework.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        return self.serializer_class

    @extend_schema(parameters=CALENDAR_DATE_RANGE_PARAMETERS)
    def get(self, request, *args, **kwargs):
        """
        Return a list of all homework instances for the given course. For convenience, homework instances on a GET are
        serialized with representations of associated attachments and reminders to avoid the need for redundant API
        calls.
        """
        response = super().get(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    @extend_schema(
        responses={
            201: HomeworkExtendedSerializer
        },
        examples=[
            OpenApiExample(
                'new_ungraded_assignment',
                summary='Ungraded assignment due later this term',
                description=(
                    'An ungraded assignment. `current_grade` uses the sentinel `-1/100`; the '
                    'gradebook ignores rows with that value.'
                ),
                value={
                    'title': 'Problem Set 3',
                    'all_day': False,
                    'show_end_time': False,
                    'start': '2026-09-21T23:59:00-07:00',
                    'end': '2026-09-21T23:59:00-07:00',
                    'priority': 50,
                    'comments': '',
                    'current_grade': '-1/100',
                    'completed': False,
                    'category': 4242,
                    'materials': [],
                },
                request_only=True,
            ),
            OpenApiExample(
                'completed_graded_assignment',
                summary='Completed assignment with a recorded grade',
                description=(
                    'A completed, graded assignment. `current_grade` uses the `n/d` form (87 out '
                    'of 100) and `completed` is `true`. The `category` must reference a graded '
                    'category on the same course.'
                ),
                value={
                    'title': 'Midterm Exam',
                    'all_day': False,
                    'show_end_time': True,
                    'start': '2026-10-14T10:00:00-07:00',
                    'end': '2026-10-14T11:30:00-07:00',
                    'priority': 80,
                    'comments': 'Closed book, calculators allowed.',
                    'current_grade': '87/100',
                    'completed': True,
                    'category': 4243,
                    'materials': [],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new homework instance for the given course.
        """
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)

        materials = request.data.get('materials', [])
        if materials:
            for material_id in materials:
                permissions.check_material_permission(request.user.pk, material_id)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return extended serializer with note field
        instance = serializer.instance
        response_serializer = HomeworkExtendedSerializer(instance)

        logger.info(
            f"Homework {instance.pk} created in Course {kwargs['course']} for user {request.user.pk}")

        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(
    tags=['planner.homework']
)
class CourseGroupCourseHomeworkApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course']).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'materials', 'notes_set')
        else:
            return Homework.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        return self.serializer_class

    def get(self, request, *args, **kwargs):
        """
        Return the given homework instance. For convenience, homework instances on a GET are serialized with
        representations of associated attachments and reminders to avoid the need for redundant API calls.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(responses={200: HomeworkExtendedSerializer})
    def put(self, request, *args, **kwargs):
        """
        Update the given homework instance.
        """
        permissions.check_course_permission(request.user.pk, request.data['course'])
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)
        materials = request.data.get('materials', [])
        if materials:
            for material_id in materials:
                permissions.check_material_permission(request.user.pk, material_id)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Homework {kwargs['pk']} updated for user {request.user.pk}")

        return Response(HomeworkExtendedSerializer(serializer.instance).data)

    @extend_schema(responses={200: HomeworkExtendedSerializer})
    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given homework instance.
        """
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)
        materials = request.data.get('materials', [])
        if materials:
            for material_id in materials:
                permissions.check_material_permission(request.user.pk, material_id)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Homework {kwargs['pk']} patched for user {request.user.pk}")

        return Response(HomeworkExtendedSerializer(serializer.instance).data)

    @extend_schema(
        tags=['planner.homework']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given homework instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Homework {kwargs['pk']} deleted for user {request.user.pk}")

        return response


@extend_schema(
    tags=['planner.homework']
)
class CourseGroupCourseHomeworkApiCloneView(HeliumAPIView, RetrieveModelMixin):
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Homework.objects.none()

    @extend_schema(
        request=None,
        responses={
            201: HomeworkExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Clone the given homework instance, including its reminders.
        """
        source = self.get_object()

        clone = clone_homework(source)

        return Response(HomeworkExtendedSerializer(clone).data, status=status.HTTP_201_CREATED)
