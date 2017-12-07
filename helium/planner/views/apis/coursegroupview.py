"""
Authenticated views for CourseGroup interaction.
"""

import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, RetrieveModelMixin, UpdateModelMixin, \
    DestroyModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.planner.models import CourseGroup
from helium.planner.permissions import IsOwner
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupsApiLCView(GenericAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.course_groups.all()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)


class CourseGroupsApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    queryset = CourseGroup.objects.all()
    serializer_class = CourseGroupSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
