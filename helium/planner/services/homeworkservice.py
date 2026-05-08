__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from helium.planner.models import Homework
from helium.planner.services.reminderservice import clone_reminders
from helium.planner.utils.cloneutils import next_clone_title

logger = logging.getLogger(__name__)


def clone_homework(source):
    """Clone a Homework with its reminders and materials; ``comments``, ``current_grade``, and ``completed`` are reset."""
    clone = Homework.objects.create(
        title=next_clone_title(source.title),
        all_day=source.all_day,
        show_end_time=source.show_end_time,
        start=source.start,
        end=source.end,
        priority=source.priority,
        url=source.url,
        comments='',
        current_grade='-1/100',
        completed=False,
        category=source.category,
        course=source.course,
    )
    clone.materials.set(source.materials.all())

    clone_reminders(source, clone)

    logger.info(f"Homework {source.pk} cloned to {clone.pk} for user {source.get_user().pk}")

    return clone
