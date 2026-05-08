__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from helium.planner.models import Event
from helium.planner.services.reminderservice import clone_reminders
from helium.planner.utils.cloneutils import next_clone_title

logger = logging.getLogger(__name__)


def clone_event(source):
    """Clone an Event with its reminders; ``comments`` is reset and ``owner_id`` / ``example_schedule`` are not copied."""
    clone = Event.objects.create(
        title=next_clone_title(source.title),
        all_day=source.all_day,
        show_end_time=source.show_end_time,
        start=source.start,
        end=source.end,
        priority=source.priority,
        url=source.url,
        comments='',
        user=source.user,
    )

    clone_reminders(source, clone)

    logger.info(f"Event {source.pk} cloned to {clone.pk} for user {source.user.pk}")

    return clone
