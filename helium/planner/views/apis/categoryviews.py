import logging

from rest_framework.exceptions import NotFound
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.views.apis.schemas.categoryschemas import CategoryIDSchema
from helium.planner.views.apis.schemas.courseschemas import SubCourseListSchema

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
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.filter(course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseGroupCourseCategoriesApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all category instances for the given course.

    post:
    Create a new category instance for the given course.

    Note that all weights associated with a single course cannot exceed a value of 100.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.filter(course_id=self.kwargs['course'], course__course_group__user_id=user.pk)

    def check_course_group_permission(self, request, course_group_id):
        if not CourseGroup.objects.filter(pk=course_group_id, user_id=request.user.pk).exists():
            raise NotFound('CourseGroup not found.')

    def check_course_permission(self, request, course_id):
        if not Course.objects.filter(pk=course_id, course_group__user_id=request.user.pk).exists():
            raise NotFound('Course not found.')

    def get(self, request, *args, **kwargs):
        self.check_course_group_permission(request, kwargs['course_group'])
        self.check_course_permission(request, kwargs['course'])

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        self.check_course_group_permission(request, kwargs['course_group'])
        self.check_course_permission(request, kwargs['course'])

        response = self.create(request, *args, **kwargs)

        logger.info('Category {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                          request.user.get_username()))

        metricutils.increment(request, 'action.category.created')

        return response


class CourseGroupCourseCategoriesApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
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
    schema = CategoryIDSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.filter(course__course_group_id=self.kwargs['course_group'],
                                       course_id=self.kwargs['course'],
                                       course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('Category {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.category.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'Category {} deleted from Course {} for user {}'.format(kwargs['pk'], kwargs['course'],
                                                                    request.user.get_username()))

        metricutils.increment(request, 'action.category.deleted')

        return response
