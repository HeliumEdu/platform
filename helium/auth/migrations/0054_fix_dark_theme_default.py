from datetime import datetime, timezone

from django.db import migrations
from django.db.models import Q

# Migration 0028 (2026-01-24) introduced ``color_scheme_theme`` with an
# accidental default of DARK (1). Migration 0030 corrected the default to
# SYSTEM (2) but did not touch existing rows. This data migration repairs
# settings for users who never saw the dark default in the new frontend, so
# the correction is invisible to them.

FEATURE_ADDED_AT = datetime(2026, 1, 24, tzinfo=timezone.utc)
DARK = 1
SYSTEM = 2


def fix_dark_theme_default(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')

    UserSettings.objects.filter(color_scheme_theme=DARK).filter(
        Q(user__last_login__isnull=True) | Q(user__last_login__lt=FEATURE_ADDED_AT)
    ).update(color_scheme_theme=SYSTEM)


class Migration(migrations.Migration):
    dependencies = [
        ('helium_auth', '0053_alter_usersettings_review_prompts_requested'),
    ]

    operations = [
        migrations.RunPython(fix_dark_theme_default, migrations.RunPython.noop),
    ]
