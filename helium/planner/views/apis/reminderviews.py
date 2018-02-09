import logging

from rest_framework.generics import GenericAPIView
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.utils import metricutils
from helium.planner import permissions
from helium.planner.filters import ReminderFilter
from helium.planner.schemas import ReminderDetailSchema
from helium.planner.serializers.reminderserializer import ReminderSerializer, ReminderExtendedSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.2.1'

logger = logging.getLogger(__name__)


class RemindersApiListView(GenericAPIView, CreateModelMixin, ListModelMixin):
    """
    get:
    Return a list of all reminder instances for the authenticated user. For convenience, reminder instances on a GET are
    serialized to a depth of two to avoid the need for redundant API calls.

    post:
    Create a new reminder instance for the authenticated user.

    For more details pertaining to choice field values, [see here](https://github.com/HeliumEdu/platform/wiki#choices).
    """
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)
    filter_class = ReminderFilter

    def get_queryset(self):
        user = self.request.user
        return user.reminders.all()

    def get(self, request, *args, **kwargs):
        self.serializer_class = ReminderExtendedSerializer

        return self.list(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])

        response = self.create(request, *args, **kwargs)

        logger.info('Reminder {} created for user {}'.format(response.data['id'], request.user.get_username()))

        metricutils.increment('action.reminder.created', request)

        return response


class RemindersApiDetailView(GenericAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    """
    get:
    Return the given reminder instance. For convenience, reminder instances on a GET are serialized to a depth of two
    to avoid the need for redundant API calls.

    put:
    Update the given reminder instance.

    patch:
    Update only the given attributes of the given reminder instance.

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
        self.serializer_class = ReminderExtendedSerializer

        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        elif 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])

        response = self.partial_update(request, *args, **kwargs)

        logger.info('Reminder {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.reminder.updated', request)

        return response

    def patch(self, request, *args, **kwargs):
        response = self.partial_update(request, *args, **kwargs)

        logger.info('Reminder {} updated for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.reminder.updated', request)

        return response

    def delete(self, request, *args, **kwargs):
        response = self.destroy(request, *args, **kwargs)

        logger.info('Reminder {} deleted for user {}'.format(kwargs['pk'], request.user.get_username()))

        metricutils.increment('action.reminder.deleted', request)

        return response
