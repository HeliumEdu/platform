import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework import filters, status
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common import enums
from helium.common.permissions import IsOwner
from helium.common.search import HeliumSearchFilter
from helium.common.views.base import IF_MATCH_PARAMETER, HeliumAPIView, PreconditionMixin
from helium.planner import permissions
from helium.planner.filters import HomeworkFilter
from helium.planner.models import Homework
from helium.planner.permissions import IsCourseGroupOwner, IsCourseOwner
from helium.planner.serializers.homeworkserializer import HomeworkSerializer, HomeworkExtendedSerializer
from helium.planner.services.homeworkservice import clone_homework
from helium.planner.views.base import HeliumCalendarItemAPIView, CALENDAR_DATE_RANGE_PARAMETERS, SCOPE_ALL, \
    OCCURRENCE_START_PARAMETER, RepeatingItemDetailMixin, occurrence_start_param, scope_parameter

logger = logging.getLogger(__name__)


def _requested_resource_ids(request):
    return request.data.get('resources') or []


@extend_schema(
    tags=['planner.homework']
)
class UserHomeworkApiListView(HeliumCalendarItemAPIView):
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.OrderingFilter, HeliumSearchFilter,)
    filterset_class = HomeworkFilter
    search_fields = ('title', 'category__title', 'course__title',)
    search_description = 'Search by title, category title, and class title.'
    ordering_fields = ('start', 'title', 'completed', 'priority', 'category__title', 'course__title',)

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Homework.objects.for_user(user.pk).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'resources', 'notes_set')
        else:
            return Homework.objects.none()

    @extend_schema(
        summary='List all Homework for the User',
        parameters=CALENDAR_DATE_RANGE_PARAMETERS,
    )
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
    search_fields = ('title', 'category__title', 'course__title',)
    search_description = 'Search by title, category title, and class title.'

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course']).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'resources', 'notes_set')
        else:
            return Homework.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        return self.serializer_class

    @extend_schema(
        summary='List Homework for a Course',
        parameters=CALENDAR_DATE_RANGE_PARAMETERS,
    )
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
        summary='Create Homework for a Course',
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
                    'current_grade': enums.UNGRADED,
                    'completed': False,
                    'category': 4242,
                    'resources': [],
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
                    'current_grade': '87/100',
                    'completed': True,
                    'category': 4243,
                    'resources': [],
                },
                request_only=True,
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new homework instance for the given course.
        """
        for course_id in permissions.requested_ids(request.data, 'course'):
            permissions.check_course_permission(request.user.pk, course_id)
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)

        for resource_id in _requested_resource_ids(request):
            permissions.check_resource_permission(request.user.pk, resource_id)

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
class CourseGroupCourseHomeworkApiDetailView(RepeatingItemDetailMixin, PreconditionMixin, HeliumAPIView,
                                             RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = HomeworkSerializer
    precondition_serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course']).select_related('category', 'course').prefetch_related('attachments', 'reminders', 'resources', 'notes_set')
        else:
            return Homework.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        return self.serializer_class

    @extend_schema(summary='Retrieve a Homework')
    def get(self, request, *args, **kwargs):
        """
        Return the given homework instance. For convenience, homework instances on a GET are serialized with
        representations of associated attachments and reminders to avoid the need for redundant API calls.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(summary='Update a Homework', parameters=[IF_MATCH_PARAMETER],
                   responses={200: HomeworkExtendedSerializer})
    def put(self, request, *args, **kwargs):
        """
        Update the given homework instance.
        """
        permissions.check_course_permission(request.user.pk, request.data['course'])
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)
        for resource_id in _requested_resource_ids(request):
            permissions.check_resource_permission(request.user.pk, resource_id)

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        logger.info(f"Homework {kwargs['pk']} updated for user {request.user.pk}")

        return Response(HomeworkExtendedSerializer(serializer.instance).data)

    @extend_schema(
        summary='Partially update a Homework',
        parameters=[
            IF_MATCH_PARAMETER,
            scope_parameter(SCOPE_ALL, '`all` updates the Homework, and a repeating Homework\'s whole series. `this` '
                                       'makes the occurrence at `occurrence_start` its own Homework, with the '
                                       'series\' reminders, and leaves it out of the series, which keeps its note '
                                       'and attachments. If it was the last occurrence, they move to the new '
                                       'Homework and the series is deleted. Completing an occurrence needs `this`.'),
            OCCURRENCE_START_PARAMETER,
        ],
        responses={200: HomeworkExtendedSerializer},
    )
    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given homework instance. With `occurrence_start`, `start` / `end`
        are that occurrence's new times, and the whole series moves with it. With `scope=this`, the response is the
        new Homework.
        """
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])
        category = request.data.get('category', None)
        if category:
            permissions.check_category_permission(request.user.pk, category)
        for resource_id in _requested_resource_ids(request):
            permissions.check_resource_permission(request.user.pk, resource_id)

        return self.update_in_scope(request, HomeworkExtendedSerializer)

    @extend_schema(
        summary='Delete a Homework',
        parameters=[
            IF_MATCH_PARAMETER,
            scope_parameter(SCOPE_ALL, '`all` deletes the Homework, and a repeating Homework\'s whole series. `this` '
                                       'deletes only the occurrence at `occurrence_start`; deleting the last one '
                                       'deletes the series.'),
            OCCURRENCE_START_PARAMETER,
        ],
        tags=['planner.homework']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given homework instance.
        """
        return self.destroy_in_scope(request, *args, **kwargs)


@extend_schema(
    tags=['planner.homework']
)
class CourseGroupCourseHomeworkApiCloneView(HeliumAPIView, RetrieveModelMixin):
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if self.has_request_user():
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Homework.objects.none()

    @extend_schema(
        summary='Clone a Homework',
        request=None,
        parameters=[OCCURRENCE_START_PARAMETER],
        responses={
            201: HomeworkExtendedSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Clone the given homework instance, including its reminders. A repeating homework is cloned at the occurrence
        at `occurrence_start`, or at its `start` when omitted, and the clone doesn't repeat.
        """
        source = self.get_object()

        clone = clone_homework(source, occurrence_start_param(request, required=False))

        return Response(HomeworkExtendedSerializer(clone).data, status=status.HTTP_201_CREATED)
