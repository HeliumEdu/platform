__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from helium.common import enums
from helium.planner.models import Category

logger = logging.getLogger(__name__)


def seed_categories(course_id: int, template: int) -> None:
    """
    Provision the default categories for the given template on a course.

    Idempotent via ``get_or_create`` on ``(course, title)``, so it respects the
    ``unique_together('course', 'title')`` constraint and is safe to re-run.

    :param course_id: the primary key of the course to provision categories on.
    :param template: the template to provision (a key of ``enums.CATEGORY_TEMPLATES``).
    """
    for definition in enums.CATEGORY_TEMPLATES[template]:
        Category.objects.get_or_create(
            course_id=course_id,
            title=definition['title'],
            defaults={'weight': 0, 'color': definition['color']},
        )

    logger.info(f"Seeded '{template}' default categories for Course {course_id}")
