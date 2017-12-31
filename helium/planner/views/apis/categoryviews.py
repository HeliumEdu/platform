import logging

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.permissions import IsOwner
from helium.planner.serializers.categoryserializer import CategorySerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserCategoriesApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all category instances for the authenticated user.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return Category.objects.filter(course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseGroupCourseCategoriesApiListView(GenericAPIView):
    """
    get:
    Return a list of all category instances for the given course.

    post:
    Create a new category instance for the given course.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id).exists():
            raise NotFound('CourseGroup not found.')
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id).exists():
            raise NotFound('Course not found.')
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            self.permission_denied(request, 'You do not have permission to perform this action.')

    def get(self, request, course_group_id, course_id, format=None):
        self.check_course_group_permission(request, course_group_id)
        self.check_course_permission(request, course_id)

        categories = Category.objects.filter(course_id=course_id)

        serializer = self.get_serializer(categories, many=True)

        return Response(serializer.data)

    def post(self, request, course_group_id, course_id, format=None):
        self.check_course_group_permission(request, course_group_id)
        self.check_course_permission(request, course_id)

        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            serializer.save(course_id=course_id)

            logger.info('Category {} created in Course {} for user {}'.format(serializer.instance.pk, course_id,
                                                                              request.user.get_username()))

            metricutils.increment(request, 'action.category.created')

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourseGroupCourseCategoriesApiDetailView(GenericAPIView):
    """
    get:
    Return the given category instance.

    put:
    Update the given category instance.

    delete:
    Delete the given category instance.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_object(self, request, course_group_id, course_id, pk):
        try:
            return Category.objects.get(course__course_group_id=course_group_id, course_id=course_id, pk=pk)
        except Category.DoesNotExist:
            raise Http404

    def get(self, request, course_group_id, course_id, pk, format=None):
        category = self.get_object(request, course_group_id, course_id, pk)
        self.check_object_permissions(request, category)

        serializer = self.get_serializer(category)

        return Response(serializer.data)

    def put(self, request, course_group_id, course_id, pk, format=None):
        category = self.get_object(request, course_group_id, course_id, pk)
        self.check_object_permissions(request, category)

        serializer = self.get_serializer(category, data=request.data)

        if serializer.is_valid():
            serializer.save()

            logger.info('Category {} updated for user {}'.format(pk, request.user.get_username()))

            metricutils.increment(request, 'action.category.updated')

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, course_group_id, course_id, pk, format=None):
        category = self.get_object(request, course_group_id, course_id, pk)
        self.check_object_permissions(request, category)

        category.delete()

        logger.info(
            'Category {} deleted from Course {} for user {}'.format(pk, course_id, request.user.get_username()))

        metricutils.increment(request, 'action.category.deleted')

        return Response(status=status.HTTP_204_NO_CONTENT)
