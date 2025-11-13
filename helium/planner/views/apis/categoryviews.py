__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, \
    CreateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner.filters import CategoryFilter
from helium.planner.models import Category
from helium.planner.permissions import IsCourseOwner, IsCourseGroupOwner
from helium.planner.serializers.categoryserializer import CategorySerializer

logger = logging.getLogger(__name__)


class UserCategoriesApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = CategoryFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk)
        else:
            return Category.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all category instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseCategoriesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filterset_class = CategoryFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Category.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all category instances for the given course.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    @extend_schema(
        responses={
            201: CategorySerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new category instance for the given course.

        Note that all weights associated with a single course cannot exceed a value of 100.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(
            f"Category {response.data['id']} created in Course {kwargs['course']} for user {request.user.get_username()}")

        return response


class CourseGroupCourseCategoriesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Category.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given category instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given category instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"Category {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given category instance.
        """
        category = self.get_object()
        homework = list(category.homework.all())

        response = self.destroy(request, *args, **kwargs)

        if len(homework) > 0:
            uncategorized = Category.objects.get_uncategorized(category.course_id)
            for h in homework:
                h.category = uncategorized
                h.save()

                logger.info(
                    f'Homework {h.pk} category set to Uncategorized {uncategorized.pk} for user {request.user.get_username()}')

        logger.info(
            f"Category {kwargs['pk']} deleted from Course {kwargs['course']} for user {request.user.get_username()}")

        return response
