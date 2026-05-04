__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from helium.auth.serializers.usersettingsserializer import UserSettingsSerializer
from helium.common.utils import taskutils
from helium.common.utils.commonutils import local_midnight_as_utc
from helium.common.views.base import HeliumAPIView
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.planner.models import Course, Event, Homework, Reminder
from helium.planner.services import coursescheduleservice
from helium.planner.tasks import adjust_reminder_times

logger = logging.getLogger(__name__)


class UserSettingsApiDetailView(HeliumAPIView):
    queryset = get_user_model().objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def put(self, request, *args, **kwargs):
        """
        Update the authenticated user's settings. This endpoint only updates the fields given (i.e. no need to PATCH
        for partials data).
        """
        user = self.get_object()

        old_time_zone = user.settings.time_zone

        serializer = self.get_serializer(user.settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        new_time_zone = serializer.data.get('time_zone')
        if new_time_zone and new_time_zone != old_time_zone:
            # Run synchronously so the next GET reflects the rebased dates. Otherwise the
            # client (which may already be rendering the planner) would briefly show all-day
            # events spanning two days in the new timezone.
            _normalize_all_day_for_timezone_change(user, old_time_zone, new_time_zone)

        logger.info(f'Settings updated for user {user.pk}')

        return Response(serializer.data)


def _normalize_all_day_for_timezone_change(user, old_time_zone, new_time_zone):
    """
    Rebase all-day CalendarItem rows for `user` so they remain pinned to the same local
    date after a timezone change.

    All-day items are stored as `DateTimeField`s representing midnight-in-user-tz, converted
    to UTC. When `time_zone` changes, the stored UTC values no longer align with midnight in
    the new tz, so we recompute `start`/`end` to properly align with midnight in the new
    timezone, on the same day as the original.
    """
    old_tz = ZoneInfo(old_time_zone)
    new_tz = ZoneInfo(new_time_zone)

    _rebase_all_day(user, Event, old_tz, new_tz, reminder_field='event')
    _rebase_all_day(user, Homework, old_tz, new_tz, reminder_field='homework')

    _invalidate_user_calendar_caches(user)

    logger.info(f'Normalized all-day calendar items for user {user.pk} after timezone '
                f'change ({old_time_zone} -> {new_time_zone})')


def _rebase_all_day(user, model_cls, old_tz, new_tz, reminder_field):
    items_to_update = []
    for item in (model_cls.objects.for_user(user.pk)
                 .filter(all_day=True)
                 .iterator()):
        start_date = item.start.astimezone(old_tz).date()
        end_date = item.end.astimezone(old_tz).date()
        item.start = local_midnight_as_utc(start_date, new_tz)
        item.end = local_midnight_as_utc(end_date, new_tz)
        items_to_update.append(item)

    if not items_to_update:
        return

    model_cls.objects.bulk_update(items_to_update, ['start', 'end'])

    ids_with_reminders = set(
        Reminder.objects
        .filter(**{f'{reminder_field}__in': [i.pk for i in items_to_update]})
        .values_list(f'{reminder_field}_id', flat=True)
        .distinct()
    )
    for item in items_to_update:
        if item.pk in ids_with_reminders:
            taskutils.safe_apply_async(
                adjust_reminder_times,
                args=(item.pk, item.calendar_item_type),
                priority=settings.CELERY_PRIORITY_LOW,
            )


def _invalidate_user_calendar_caches(user):
    for course in Course.objects.for_user(user.pk).iterator():
        coursescheduleservice.clear_cached_course_schedule(course)
    for external_calendar in ExternalCalendar.objects.for_user(user.pk).iterator():
        icalexternalcalendarservice.invalidate_calendar_cache(external_calendar)
