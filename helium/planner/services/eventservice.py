__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from helium.planner.models import Event
from helium.planner.services.reminderservice import clone_reminders
from helium.planner.utils.cloneutils import next_clone_title

logger = logging.getLogger(__name__)


def clone_event(source):
    """
    Create a clone of an Event, including its reminders.

    The clone inherits scheduling and configuration fields (title with an incremented suffix, dates,
    priority, url) from the source. Per-instance content is reset: ``comments`` is cleared. The
    ``owner_id`` and ``example_schedule`` fields are intentionally not copied — clones are
    user-initiated and never represent an externally-owned or example-schedule item. Notes and
    attachments are not copied — they are instance-specific content.

    Reminders attached to the source are cloned via ``clone_reminders`` so the new event starts
    with the same reminder configuration, anchored to its (initially identical) start time.
    """
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
