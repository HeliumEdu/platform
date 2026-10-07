from datetime import timedelta

from django.db import migrations
from django.db.models import Min

#: The window the former runtime fallback allowed after an unstamped example schedule was created.
LEGACY_IMPORT_WINDOW = timedelta(seconds=30)


def backfill_example_schedule_imported_at(apps, schema_editor):
    """Stamp every unstamped user who still has example schedule data with its creation time plus the old window."""
    User = apps.get_model('helium_auth', 'User')

    earliest = {}
    for app_label, model_name in (('feed', 'ExternalCalendar'), ('planner', 'CourseGroup'),
                                  ('planner', 'MaterialGroup'), ('planner', 'Event'), ('planner', 'Note')):
        model = apps.get_model(app_label, model_name)
        rows = (model.objects
                .filter(example_schedule=True, user__example_schedule_imported_at__isnull=True)
                .values('user_id')
                .annotate(first=Min('created_at')))
        for row in rows:
            current = earliest.get(row['user_id'])
            if current is None or row['first'] < current:
                earliest[row['user_id']] = row['first']

    for user_id, created_at in earliest.items():
        User.objects.filter(pk=user_id, example_schedule_imported_at__isnull=True).update(
            example_schedule_imported_at=created_at + LEGACY_IMPORT_WINDOW)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0076_usersettings_getting_started_last_shown_at'),
        ('feed', '0016_alter_externalcalendar_last_sync_error'),
        ('planner', '0071_alter_homework_current_grade_help_text'),
    ]

    operations = [
        migrations.RunPython(backfill_example_schedule_imported_at, migrations.RunPython.noop),
    ]
