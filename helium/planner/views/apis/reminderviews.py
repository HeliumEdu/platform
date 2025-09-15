__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.views.views import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import ReminderFilter
from helium.planner.models import Reminder
from helium.planner.serializers.reminderserializer import ReminderSerializer, ReminderExtendedSerializer

logger = logging.getLogger(__name__)


class RemindersApiListView(HeliumAPIView, CreateModelMixin, ListModelMixin):
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ReminderFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.reminders.all()
        else:
            return Reminder.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return a list of all reminder instances for the authenticated user. For convenience, reminder instances on a GET are
        serialized to a depth of two to avoid the need for redundant API calls.
        """
        self.serializer_class = ReminderExtendedSerializer

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def post(self, request, *args, **kwargs):
        """
        Create a new reminder instance for the authenticated user.
        """
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])

        response = self.create(request, *args, **kwargs)

        logger.info(f"Reminder {response.data['id']} created for user {request.user.get_username()}")

        return response


class RemindersApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            return user.reminders.all()
        else:
            return Reminder.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Return the given reminder instance. For convenience, reminder instances on a GET are serialized to a depth of
        two to avoid the need for redundant API calls.
        """
        self.serializer_class = ReminderExtendedSerializer

        response = self.retrieve(request, *args, **kwargs)

        return response

    def put(self, request, *args, **kwargs):
        """
        Update the given reminder instance.
        """
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        elif 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])

        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given reminder instance.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} updated for user {request.user.get_username()}")

        return response

    def delete(self, request, *args, **kwargs):
        """
        Delete the given reminder instance.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} deleted for user {request.user.get_username()}")

        return response
