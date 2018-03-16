import logging

from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner.models import Category
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.schemas import CategoryDetailSchema, SubCourseListSchema
from helium.planner.serializers.categoryserializer import CategorySerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


class UserCategoriesApiListView(HeliumAPIView, ListModelMixin):
    """
    get:
    Return a list of all category instances for the authenticated user.
    """
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Category.objects.for_user(user.pk)
        else:
            Category.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseCategoriesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
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
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            Category.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        response = self.create(request, *args, **kwargs)

        logger.info('Category {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                          request.user.get_username()))

        return response


class CourseGroupCourseCategoriesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
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
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            Category.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        response = self.update(request, *args, **kwargs)

        logger.info('Category {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        return response

    def delete(self, request, *args, **kwargs):
        category = self.get_object()
        homework = list(category.homework.all())

        response = self.destroy(request, *args, **kwargs)

        if len(homework) > 0:
            uncategorized = Category.objects.get_uncategorized(category.course_id)
            for h in homework:
                h.category = uncategorized
                h.save()

                logger.info(
                    'Homework {} category set to Uncategorized {} for user {}'.format(h.pk, uncategorized.pk,
                                                                                      request.user.get_username()))

        logger.info(
            'Category {} deleted from Course {} for user {}'.format(kwargs['pk'], kwargs['course'],
                                                                    request.user.get_username()))

        return response
