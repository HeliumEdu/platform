__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework.mixins import RetrieveModelMixin, DestroyModelMixin, CreateModelMixin, \
    UpdateModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated

from helium.common.permissions import IsOwner
from helium.common.tasks import send_dismiss_pushes
from helium.common.utils import taskutils
from helium.common.views.base import HeliumAPIView
from helium.planner import permissions
from helium.planner.filters import ReminderFilter
from helium.planner.models import Reminder
from helium.planner.serializers.reminderserializer import ReminderSerializer, ReminderExtendedSerializer

logger = logging.getLogger(__name__)


@extend_schema(
    tags=['planner.reminder']
)
class RemindersApiListView(HeliumAPIView, CreateModelMixin, ListModelMixin):
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated,)
    filterset_class = ReminderFilter

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            queryset = user.reminders.all().select_related(
                'homework__category',
                'homework__course',
                'event__user',
                'course',
            ).prefetch_related(
                'homework__attachments',
                'homework__reminders',
                'homework__materials',
                'event__attachments',
                'event__reminders',
                'course__schedules',
            )

            # Frontend clients prior to 3.5.0 don't send X-Client-Version, and also have a bug
            # where they'll crash on /notifications if course-based reminders are returned, so
            # exclude them; this guard (and the one below) can be removed once all users are
            # on 3.5.0 and higher
            if not self.request.headers.get('X-Client-Version'):
                queryset = queryset.exclude(homework=None, event=None, course__isnull=False)

            return queryset
        else:
            return Reminder.objects.none()

    @extend_schema(
        summary='List Reminders for the User',
        tags=['planner.reminder'],
        responses={200: ReminderExtendedSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        """
        Return all reminders for the authenticated user. The parent `homework`, `event`, or `course` is nested inline.
        """
        self.serializer_class = ReminderExtendedSerializer

        response = self.list(request, *args, **kwargs)

        return response

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary='Create a Reminder',
        responses={
            201: ReminderSerializer
        }
    )
    def post(self, request, *args, **kwargs):
        """
        Create a reminder for the authenticated user.

        Exactly one of `event`, `homework`, or `course` must be given — that's the parent the reminder
        fires against. `course`-typed reminders are repeating: only one active reminder is kept per
        (`course`, `type`, `offset`, `offset_type`) combination, and the next occurrence is rolled
        forward by the server as each one fires.
        """
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        if 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])
        if 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])

        response = self.create(request, *args, **kwargs)

        logger.info(f"Reminder {response.data['id']} created for user {request.user.pk}")

        return response


@extend_schema(
    tags=['planner.reminder']
)
class RemindersApiDetailView(HeliumAPIView, RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin):
    serializer_class = ReminderSerializer
    permission_classes = (IsAuthenticated, IsOwner,)

    def get_queryset(self):
        if hasattr(self.request, 'user') and not getattr(self, "swagger_fake_view", False):
            user = self.request.user
            queryset = user.reminders.all().select_related(
                'homework__category',
                'homework__course',
                'event__user',
                'course',
            ).prefetch_related(
                'homework__attachments',
                'homework__reminders',
                'homework__materials',
                'event__attachments',
                'event__reminders'
            )

            # Frontend clients prior to 3.5.0 don't send X-Client-Version, and also have a bug
            # where they'll crash on /notifications if course-based reminders are returned, so
            # exclude them; this guard (and the one above) can be removed once all users are
            # on 3.5.0 and higher
            if not self.request.headers.get('X-Client-Version'):
                queryset = queryset.exclude(homework=None, event=None, course__isnull=False)

            return queryset
        else:
            return Reminder.objects.none()

    @extend_schema(summary='Retrieve a Reminder', responses={200: ReminderExtendedSerializer})
    def get(self, request, *args, **kwargs):
        """
        Return the given reminder instance. The parent `homework`, `event`, or `course` is nested inline.
        """
        self.serializer_class = ReminderExtendedSerializer

        response = self.retrieve(request, *args, **kwargs)

        return response

    @extend_schema(summary='Update a Reminder')
    def put(self, request, *args, **kwargs):
        """
        Update the given reminder instance.
        """
        if 'event' in request.data:
            permissions.check_event_permission(request.user.pk, request.data['event'])
        elif 'homework' in request.data:
            permissions.check_homework_permission(request.user.pk, request.data['homework'])
        elif 'course' in request.data:
            permissions.check_course_permission(request.user.pk, request.data['course'])

        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} updated for user {request.user.pk}")

        return response

    @extend_schema(summary='Partially update a Reminder')
    def patch(self, request, *args, **kwargs):
        """
        Update only the given attributes of the given reminder instance.
        """
        response = self.partial_update(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} updated for user {request.user.pk}")

        return response

    def perform_update(self, serializer):
        was_dismissed = Reminder.objects.values_list('dismissed', flat=True).get(
            pk=serializer.instance.pk
        )
        reminder = serializer.save()

        # On the false->true dismiss transition, clear the reminder's already-
        # delivered push from all of the user's devices.
        if reminder.dismissed and not was_dismissed:
            push_tokens = list(
                {t.device_id: t.token for t in reminder.user.push_tokens.all()}.values()
            )
            if push_tokens:
                taskutils.safe_apply_async(
                    send_dismiss_pushes,
                    args=(push_tokens, reminder.pk),
                    priority=settings.CELERY_PRIORITY_HIGH,
                )

    def perform_destroy(self, instance):
        if instance.course_id:
            Reminder.objects.filter(
                course_id=instance.course_id,
                user_id=instance.user_id,
                type=instance.type,
                offset=instance.offset,
                offset_type=instance.offset_type,
            ).delete()
            Reminder.objects.filter(
                course_id=instance.course_id,
                user_id=instance.user_id,
                type=instance.type,
                sent=True,
                dismissed=False,
            ).delete()
        else:
            instance.delete()

    @extend_schema(
        summary='Delete a Reminder',
        tags=['planner.reminder']
    )
    def delete(self, request, *args, **kwargs):
        """
        Delete the given reminder.

        For `course`-typed reminders, this also deletes every active reminder in the same series
        (matched on `course`, `type`, `offset`, `offset_type`) plus any past sent-but-undismissed
        reminders for that `course` / `type` — so the series is fully torn down, not just the
        single targeted row.
        """
        response = self.destroy(request, *args, **kwargs)

        logger.info(f"Reminder {kwargs['pk']} deleted for user {request.user.pk}")

        return response
