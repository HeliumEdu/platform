"""
Authenticated views for CourseGroup interaction.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from helium.planner.models import CourseGroup
from helium.planner.permissions import IsOwner
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupsApiListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, format=None):
        course_groups = CourseGroup.objects.filter(user__id=request.user.pk)

        serializer = CourseGroupSerializer(course_groups, many=True)

        return Response(serializer.data)

    def post(self, request, format=None):
        serializer = CourseGroupSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)

            logger.info('CourseGroup {} created for user {}'.format(serializer.instance.pk,
                                                                    request.user.get_username()))

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseGroupsApiDetailView(APIView):
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_object(self, request, pk):
        try:
            return CourseGroup.objects.get(pk=pk)
        except CourseGroup.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        course_group = self.get_object(request, pk)
        self.check_object_permissions(request, course_group)

        serializer = CourseGroupSerializer(course_group)

        return Response(serializer.data)

    def put(self, request, pk, format=None):
        course_group = self.get_object(request, pk)
        self.check_object_permissions(request, course_group)

        serializer = CourseGroupSerializer(course_group, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('CourseGroup {} updated for user {}'.format(serializer.instance.pk,
                                                                    request.user.get_username()))

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        course_group = self.get_object(request, pk)
        self.check_object_permissions(request, course_group)

        logger.info('CourseGroup {} deleted for user {}'.format(course_group.pk,
                                                                request.user.get_username()))

        course_group.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
