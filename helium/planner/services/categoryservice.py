import logging

from helium.common import enums
from helium.planner.models import Category

logger = logging.getLogger(__name__)


def seed_categories(course_id: int, template: int) -> None:
    """
    Provision the default categories for the given template on a course.

    Idempotent on ``(course, title)``, so it respects the ``unique_together('course', 'title')``
    constraint and is safe to re-run.

    :param course_id: the primary key of the course to provision categories on.
    :param template: the template to provision (a key of ``enums.CATEGORY_TEMPLATES``).
    """
    existing_titles = set(Category.objects.filter(course_id=course_id).values_list('title', flat=True))

    for definition in enums.CATEGORY_TEMPLATES[template]:
        if definition['title'] in existing_titles:
            continue
        Category.objects.create(
            course_id=course_id,
            title=definition['title'],
            weight=0,
            color=definition['color'],
        )

    logger.info(f"Seeded '{template}' default categories for Course {course_id}")
