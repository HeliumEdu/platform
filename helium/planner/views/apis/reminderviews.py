import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, ListModelMixin, CreateModelMixin, \
    UpdateModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.views.apis.schemas.eventschemas import SubEventListSchema
from helium.planner.views.apis.schemas.homeworkschemas import SubHomeworkListSchema
from helium.planner.views.apis.schemas.reminderschemas import ReminderDetailSchema

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class EventRemindersApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all reminder instances for the given course.
    """
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)
    schema = SubEventListSchema()

    def get_queryset(self):
        user = self.request.user
        return user.reminders.filter(event_id=self.kwargs['event'])

    def get(self, request, *args, **kwargs):
        permissions.check_event_permission(request, kwargs['event'])

        response = self.list(request, *args, **kwargs)

        return response


class CourseGroupCourseHomeworkRemindersApiListView(GenericAPIView, ListModelMixin):
    """
    get:
    Return a list of all reminder instances for the given course.
    """
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)
    schema = SubHomeworkListSchema()

    def get_queryset(self):
        user = self.request.user
        return user.reminders.filter(homework_id=self.kwargs['homework'])

    def get(self, request, *args, **kwargs):
        permissions.check_course_group_permission(request, kwargs['course_group'])
        permissions.check_course_permission(request, kwargs['course'])
        permissions.check_homework_permission(request, kwargs['homework'])

        response = self.list(request, *args, **kwargs)

        return response


class RemindersApiListView(GenericAPIView, ListModelMixin, CreateModelMixin):
    """
    get:
    Return a list of all reminder instances for the authenticated user.

    post:
    Create a new reminder instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        user = self.request.user
        return user.reminders.all()

    def get(self, request, *args, **kwargs):
        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        if 'event' in request.data:
            permissions.check_event_permission(request, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request, request.data['homework'])

        response = self.create(request, *args, **kwargs)

        logger.info('Reminder {} created for user {}'.format(response.data['id'], request.user.get_username()))

        metricutils.increment(request, 'action.reminder.created')

        return response


class RemindersApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given reminder instance.

    put:
    Update the given reminder instance.

    delete:
    Delete the given reminder instance.
    """
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated, IsOwner,)
    schema = ReminderDetailSchema()

    def get_queryset(self):
        user = self.request.user
        return user.reminders.all()

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if 'event' in request.data:
            permissions.check_event_permission(request, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request, request.data['homework'])

        response = self.update(request, *args, **kwargs)

        logger.info('Reminder {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.reminder.updated')

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Reminder {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment(request, 'action.reminder.deleted')

        return response
