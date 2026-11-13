import logging

from helium.common import enums
from helium.planner.models import Homework
from helium.planner.services.recurrenceservice import find_occurrence
from helium.planner.services.reminderservice import clone_reminders
from helium.planner.utils.cloneutils import next_clone_title

logger = logging.getLogger(__name__)


def clone_homework(source, occurrence_start=None):
    """
    Clone a Homework with its reminders and resources as a single Homework; ``current_grade`` and ``completed`` are
    reset and the recurrence rule is not copied. With ``occurrence_start``, the clone takes that occurrence's times.
    """
    start, end = source.start, source.end
    if occurrence_start is not None:
        start, end = find_occurrence(source, occurrence_start)

    clone = Homework.objects.create(
        title=next_clone_title(source.title),
        all_day=source.all_day,
        show_end_time=source.show_end_time,
        start=start,
        end=end,
        priority=source.priority,
        url=source.url,
        current_grade=enums.UNGRADED,
        completed=False,
        category=source.category,
        course=source.course,
    )
    clone.resources.set(source.resources.all())

    clone_reminders(source, clone)

    logger.info(f"Homework {source.pk} cloned to {clone.pk} for user {source.get_user().pk}")

    return clone
