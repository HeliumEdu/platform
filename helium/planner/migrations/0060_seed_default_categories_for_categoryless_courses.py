__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations

from helium.common import enums


def seed_missing_default_categories(apps, schema_editor):
    """
    Heal courses that were persisted with zero categories back when category seeding was a
    non-atomic, client-side sequence of requests (a partial failure could leave a course with no
    categories). Seeding here is idempotent via get_or_create on (course, title).
    """
    Course = apps.get_model('planner', 'Course')
    Category = apps.get_model('planner', 'Category')

    for course in Course.objects.filter(categories__isnull=True).iterator():
        for definition in enums.CATEGORY_TEMPLATES[enums.STANDARD]:
            Category.objects.get_or_create(
                course_id=course.pk,
                title=definition['title'],
                defaults={'weight': 0, 'color': definition['color']},
            )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0059_alter_courseschedule_course_drop_unique'),
    ]

    operations = [
        migrations.RunPython(seed_missing_default_categories, noop_reverse),
    ]
