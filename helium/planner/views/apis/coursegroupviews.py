__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.19"

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.base import HeliumAPIView
from helium.planner.filters import CourseGroupFilter
from helium.planner.models import CourseGroup
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.coursegroup']
)
class CourseGroupsApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = CourseGroupFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.course_groups.all()
        else:
            return CourseGroup.objects.none()

    @extend_schema(
        tags=['planner.coursegroup', 'calendar.user']
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all course group instances for the authenticated user.
        """
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        responses={
            201: CourseGroupSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new course group instance for the authenticated user.
        """
        response = self.create(request, *args, **kwargs)

        logger.info(f"CourseGroup {response.data['id']} created for user {request.user.get_username()}")

        return response

@extend_schema(
    tags=['planner.coursegroup']
)
class CourseGroupsApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.course_groups.all()
        else:
            return CourseGroup.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given course group instance.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given course group instance.
        """
        response = self.update(request, *args, **kwargs)

        logger.info(f"CourseGroup {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given course group instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"CourseGroup {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
