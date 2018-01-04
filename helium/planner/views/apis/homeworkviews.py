import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.models import Homework
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.views.apis.schemas.courseschemas import SubCourseListSchema
from helium.planner.views.apis.schemas.homeworkschemas import HomeworkDetailSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class UserHomeworkApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all homework instances for the authenticated user.
    """
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated,)
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Homework.objects.filter(course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseHomeworkApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all homework instances for the given course.

    post:
    Create a new homework instance for the given course.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated,)
    schema = SubCourseListSchema()

    def get_queryset(self):
        user = self.request.user
        return Homework.objects.filter(course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        permissions.check_course_group_permission(request, kwargs['course_group'])
        permissions.check_course_permission(request, kwargs['course'])

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(course_id=self.kwargs['course'])

    def post(self, request, *args, **kwargs):
        permissions.check_course_group_permission(request, kwargs['course_group'])
        permissions.check_course_permission(request, kwargs['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request, kwargs['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request, material_id)

        response = self.create(request, *args, **kwargs)

        logger.info('Category {} created in Course {} for user {}'.format(response.data['id'], kwargs['course'],
                                                                          request.user.get_username()))

        metricutils.increment(request, 'action.category.created')

        return response


class CourseGroupCourseHomeworkApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given homework instance.

    put:
    Update the given homework instance.

    delete:
    Delete the given homework instance.
    """
    serializer_class = HomeworkSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = HomeworkDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return Homework.objects.filter(course__course_group__user_id=user.pk)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        permissions.check_course_group_permission(request, kwargs['course_group'])
        permissions.check_course_permission(request, kwargs['course'])
        if 'course' in request.data:
            permissions.check_course_permission(request, request.data['course'])
        if 'category' in request.data:
            permissions.check_category_permission(request, request.data['category'])
        for material_id in request.data.get('materials', []):
            permissions.check_material_permission(request, material_id)

        response = self.update(request, *args, **kwargs)

        logger.info('Homework {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.homework.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Homework {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.homework.deleted')

        return response
