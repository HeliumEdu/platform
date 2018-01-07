import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner.models import Category
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.schemas import CategoryDetailSchema, SubCourseListSchema
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
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.for_user(user.pk)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)


class CourseGroupCourseCategoriesApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all category instances for the given course.

    post:
    Create a new category instance for the given course.

    Note that all weights associated with a single course cannot exceed a value of 100.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('Category {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                          request.user.get_username()))

        metricutils.increment('action.category.created', request)

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
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)
    schema = CategoryDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('Category {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.category.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info(
            'Category {} deleted from Course {} for user {}'.format(kwargs['pk'], kwargs['course'],
                                                                    request.user.get_username()))

        metricutils.increment('action.category.deleted', request)

        return response
