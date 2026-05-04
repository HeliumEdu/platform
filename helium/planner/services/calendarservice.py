__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from zoneinfo import ZoneInfo

from django.conf import settings

from helium.common.utils import taskutils
from helium.common.utils.dateutils import local_midnight_as_utc
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.planner.models import Course, Event, Homework, Reminder
from helium.planner.services import coursescheduleservice
from helium.planner.tasks import adjust_reminder_times

logger = logging.getLogger(__name__)


def normalize_all_day_for_timezone_change(user, old_time_zone, new_time_zone):
    """
    Rebase all-day Event/Homework rows for `user` so they remain pinned to the same local
    date after a timezone change.

    All-day items are stored as `DateTimeField`s representing midnight-in-user-tz, converted
    to UTC. When `time_zone` changes, the stored UTC values no longer align with midnight in
    the new tz, causing the item to render across two adjacent calendar days. This function
    recomputes `start`/`end` so they once again represent midnight in the user's (new)
    timezone, on the same date the user was observing in the previous timezone.

    Reminder `start_of_range` values are recomputed via `adjust_reminder_times`, and course
    schedule and external calendar caches are invalidated since their cached UTC values also
    depend on the user's timezone.
    """
    if old_time_zone == new_time_zone:
        return

    old_tz = ZoneInfo(old_time_zone)
    new_tz = ZoneInfo(new_time_zone)

    _normalize_all_day(user, Event, old_tz, new_tz, reminder_field='event')
    _normalize_all_day(user, Homework, old_tz, new_tz, reminder_field='homework')

    _invalidate_user_calendar_caches(user)

    logger.info(f'Normalized all-day calendar items for user {user.pk} after timezone '
                f'change ({old_time_zone} -> {new_time_zone})')


def _normalize_all_day(user, model_cls, old_tz, new_tz, reminder_field):
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
