__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.16.18"

import logging
from datetime import datetime, timezone

from dateutil import parser
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import filters, status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import HomeworkFilter
from helium.planner.models import Homework
from helium.planner.permissions import IsCourseGroupOwner, IsCourseOwner
from helium.planner.serializers.homeworkserializer import HomeworkSerializer, HomeworkExtendedSerializer

logger = logging.getLogger(__name__)


class UserHomeworkApiListView(HeliumAPIView, ListModelMixin):
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filterset_class = HomeworkFilter
    search_fields = ('title', 'comments', 'category__title', 'course__title',)
    order_fields = ('start', 'title', 'completed', 'priority', 'category__title', 'course__title',)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk)
        else:
            return Homework.objects.none()

    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        _from = self.request.query_params.get('from', None)
        to = self.request.query_params.get('to', None)
        if _from and to:
            _from = parser.parse(_from[0]).astimezone(timezone.utc)
            to = parser.parse(to[0]).astimezone(timezone.utc)
            queryset = queryset.filter(Q(start__range=(_from, to)) |
                                       Q(end__range=(_from, to)))

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all homework instances for the authenticated user. For convenience, homework instances on a
        GET are serialized with representations of associated attachments and reminders to avoid the need for redundant
        API calls.
        """
        # TODO: Legacy query params, will be removed
        request.query_params._mutable = True
        if 'start__gte' in request.query_params:
            request.query_params['from'] = request.query_params.pop('start__gte')
        if 'end__lt' in request.query_params:
            request.query_params['to'] = request.query_params.pop('end__lt')

        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseHomeworkApiListView(HeliumAPIView, ListModelMixin, CreateModelMixin):
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filterset_class = HomeworkFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Homework.objects.none()

    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        _from = self.request.query_params.get('from', None)
        to = self.request.query_params.get('to', None)
        if _from and to:
            _from = parser.parse(_from[0]).astimezone(timezone.utc)
            to = parser.parse(to[0]).astimezone(timezone.utc)
            queryset = queryset.filter(Q(start__range=(_from, to)) |
                                       Q(end__range=(_from, to)))

        return queryset

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        else:
            return self.serializer_class

    @extend_schema(
        parameters=[
            OpenApiParameter(name='from', type=datetime),
            OpenApiParameter(name='to', type=datetime),
        ]
    )
    def get(self, request, *args, **kwargs):
        """
        Return a list of all homework instances for the given course. For convenience, homework instances on a GET are
        serialized with representations of associated attachments and reminders to avoid the need for redundant API
        calls.
        """
        # TODO: Remap legacy query params, will be removed
        request.query_params._mutable = True
        if 'start__gte' in request.query_params:
            request.query_params['from'] = request.query_params.pop('start__gte')
        if 'end__lt' in request.query_params:
            request.query_params['to'] = request.query_params.pop('end__lt')

        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    @extend_schema(
        responses={
            201: HomeworkSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a new homework instance for the given course.
        """
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.create(request, *args, **kwargs)

        logger.info(
            f"Category {response.data['id']} created in Course {kwargs['course']} for user {request.user.get_username()}")

        return response


class CourseGroupCourseHomeworkApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return Homework.objects.for_user(user.pk).for_course(self.kwargs['course'])
        else:
            return Homework.objects.none()

    def get_serializer_class(self):
        if self.request and self.request.method == 'GET':
            return HomeworkExtendedSerializer
        else:
            return self.serializer_class

    def get(self, request, *args, **kwargs):
        """
        Return the given homework instance. For convenience, homework instances on a GET are serialized with
        representations of associated attachments and reminders to avoid the need for redundant API calls.
        """
        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given homework instance.
        """
        permissions.check_course_permission(request.user.pk, request.data['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.update(request, *args, **kwargs)

        logger.info(f"Homework {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given homework instance.
        """
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Homework {kwargs['pk']} patched for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given homework instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Homework {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
