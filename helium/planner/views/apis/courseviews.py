import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course
from helium.planner.permissions import IsOwner
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


class CourseGroupCoursesApiListView(GenericAPIView):
    """
    get:
    Return a list of all course instances for the given course group.

    post:
    Create a new course instance for the given course group.
    """
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id).exists():
            raise NotFound('CourseGroup not found.')
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get(self, request, course_group_id, format=None):
        self.check_course_group_permission(request, course_group_id)

        courses = Course.objects.filter(course_group_id=course_group_id, course_group__user_id=request.user.pk)

        serializer = self.get_serializer(courses, many=True)

        return Response(serializer.data)

    def post(self, request, course_group_id, format=None):
        self.check_course_group_permission(request, course_group_id)

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(course_group_id=course_group_id)

            logger.info(
                'Course {} created in CourseGroup {} for user {}'.format(serializer.instance.pk, course_group_id,
                                                                         self.request.user.get_username()))

            metricutils.increment(request, 'action.course.created')

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseGroupCoursesApiDetailView(GenericAPIView):
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
        if not CourseGroup.objects.filter(pk=course_group_id).exists():
            raise NotFound('CourseGroup not found.')
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get_object(self, request, course_group_id, pk):
        try:
            return Course.objects.get(course_group_id=course_group_id, pk=pk)
        except Course.DoesNotExist:
            raise Http404

    def get(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)

        serializer = self.get_serializer(course)

        return Response(serializer.data)

    def put(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)
        if 'course_group' in request.data:
            self.check_course_group_permission(request, request.data['course_group'])

        serializer = self.get_serializer(course, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Course {} updated for user {}'.format(pk, request.user.get_username()))

            metricutils.increment(request, 'action.course.updated')

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)

        course.delete()

        logger.info('Course {} deleted from CourseGroup {} for user {}'.format(pk, course_group_id,
                                                                               request.user.get_username()))

        metricutils.increment(request, 'action.course.deleted')

        return Response(status=status.HTTP_204_NO_CONTENT)
