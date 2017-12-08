"""
Authenticated views for Course interaction.
"""

import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.planner.models import CourseGroup, Course
from helium.planner.permissions import IsOwner
from helium.planner.serializers.courseserializer import CourseSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserCoursesApiListView(GenericAPIView, ListModelMixin):
    serializer_class = CourseSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Course.objects.filter(course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseGroupCoursesApiLCView(APIView):
    permission_classes = (IsAuthenticated,)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id).exists():
            raise NotFound('CourseGroup not found.')
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get(self, request, course_group_id, format=None):
        self.check_course_group_permission(request, course_group_id)

        courses = Course.objects.filter(course_group_id=course_group_id, course_group__user_id=request.user.pk)

        serializer = CourseSerializer(courses, many=True)

        return Response(serializer.data)

    def post(self, request, course_group_id, format=None):
        self.check_course_group_permission(request, course_group_id)

        serializer = CourseSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(course_group_id=course_group_id)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseGroupCoursesApiDetailView(APIView):
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_object(self, request, course_group_id, pk):
        try:
            return Course.objects.get(course_group_id=course_group_id, pk=pk)
        except Course.DoesNotExist:
            raise Http404

    def get(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)

        serializer = CourseSerializer(course)

        return Response(serializer.data)

    def put(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)

        serializer = CourseSerializer(course, data=request.data)

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, course_group_id, pk, format=None):
        course = self.get_object(request, course_group_id, pk)
        self.check_object_permissions(request, course)

        course.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
