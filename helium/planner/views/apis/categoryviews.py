__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
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


@extend_schema(
    tags=['planner.category', 'calendar.user']
)
class UserCategoriesApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = CategoryFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk).annotate(
                annotated_num_homework=Count('homework'),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True)),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'))
            )
        else:
            return Category.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all category instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response


@extend_schema(
    tags=['planner.category']
)
class CourseGroupCourseCategoriesApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filterset_class = CategoryFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course']).annotate(
                annotated_num_homework=Count('homework'),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True)),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'))
            )
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


@extend_schema(
    tags=['planner.category']
)
class CourseGroupCourseCategoriesApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = CategorySerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Category.objects.for_user(user.pk).for_course(self.kwargs['course']).annotate(
                annotated_num_homework=Count('homework'),
                annotated_num_homework_completed=Count('homework', filter=Q(homework__completed=True)),
                annotated_num_homework_graded=Count('homework', filter=Q(homework__completed=True) & ~Q(homework__current_grade='-1/100'))
            )
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

        if category.title == 'Uncategorized':
            raise ValidationError("The 'Uncategorized' category cannot be deleted")

        homework = list(category.homework.all())

        uncategorized = None

        if Category.objects.for_user(request.user.pk).for_course(category.course_id).count() == 1:
            logger.info(f"One category remains, creating 'Uncategorized' proactively for {request.user.get_username()}")
            uncategorized = Category.objects.get_uncategorized(category.course_id)

        if len(homework) > 0:
            if not uncategorized:
                logger.info(f"Creating 'Uncategorized' to move Homework out of category being deleted for {request.user.get_username()}")
                uncategorized = Category.objects.get_uncategorized(category.course_id)
            for h in homework:
                h.category = uncategorized
                h.save()

                logger.info(
                    f'Homework {h.pk} category set to Uncategorized {uncategorized.pk} for user {request.user.get_username()}')

        response = self.destroy(request, *args, **kwargs)

        logger.info(
            f"Category {kwargs['pk']} deleted from Course {kwargs['course']} for user {request.user.get_username()}")

        return response
