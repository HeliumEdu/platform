import logging

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.filters import HomeworkFilter
from helium.planner.models import Homework
from helium.planner.permissions import IsCourseGroupOwner, IsCourseOwner
from helium.planner.schemas import SubCourseListSchema, HomeworkDetailSchema
from helium.planner.serializers.homeworkserializer import HomeworkSerializer, HomeworkExtendedSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.7'

logger = logging.getLogger(__name__)


class UserHomeworkApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all homework instances for the authenticated user. For convenience, homework instances on a GET are
    serialized with representations of associated attachments and reminders to avoid the need for redundant API calls.
    """
    serializer_class = HomeworkExtendedSerializer
    permission_classes = (IsAuthenticated,)
    filter_backends = (DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter,)
    filter_class = HomeworkFilter
    search_fields = ('title', 'comments', 'category__title', 'course__title',)
    order_fields = ('title', 'start', 'completed', 'priority', 'category__title', 'course__title',)
    schema = SubCourseListSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
            user = self.request.user
            return Homework.objects.for_user(user.pk)
        else:
            return Homework.objects.none()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseHomeworkApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all homework instances for the given course. For convenience, homework instances on a GET are
    serialized with representations of associated attachments and reminders to avoid the need for redundant API calls.

    post:
    Create a new homework instance for the given course.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsCourseGroupOwner, IsCourseOwner)
    filter_class = HomeworkFilter
    schema = SubCourseListSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
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
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.create(request, *args, **kwargs)

        logger.info('Category {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                          request.user.get_username()))

        metricutils.increment('action.homework.created', request)

        return response


class CourseGroupCourseHomeworkApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given homework instance. For convenience, homework instances on a GET are serialized with representations
    of associated attachments and reminders to avoid the need for redundant API calls.

    put:
    Update the given homework instance.

    patch:
    Update only the given attributes of the given homework instance.

    delete:
    Delete the given homework instance.
    """
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsOwner, IsCourseGroupOwner, IsCourseOwner)
    schema = HomeworkDetailSchema()

    def get_queryset(self):
        if hasattr(self.request, 'user'):
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
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        permissions.check_course_permission(request.user.pk, request.data['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.update(request, *args, **kwargs)

        logger.info('Homework {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.homework.updated', request)

        return response

    def patch(self, request, *args, **kwargs):
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request.user.pk, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request.user.pk, material_id)

        response = self.partial_update(request, *args, **kwargs)

        logger.info('Homework {} patched for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.homework.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Homework {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.homework.deleted', request)

        return response
