__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models
from django.db.models import F, Value
from django.db.models.functions import Coalesce, Greatest


def fix_last_activity_backfill(apps, schema_editor):
    """
    Fix last_activity for users where the original backfill used created_at
    but they have more recent login timestamps.

    Sets last_activity = GREATEST(last_login, last_login_legacy, created_at)
    """
    User = apps.get_model('helium_auth', 'User')

    # Update all users to use the most recent of their activity timestamps
    # This handles:
    # - Users who only used standard login (last_login)
    # - Users who only used legacy frontend (last_login_legacy)
    # - Users who used both (takes the max)
    # - Users who never logged in (keeps created_at)
    User.objects.update(
        last_activity=Greatest(
            Coalesce(F('last_login'), F('created_at')),
            Coalesce(F('last_login_legacy'), F('created_at')),
            F('created_at'),
        )
    )


def reverse_fix(apps, schema_editor):
    """Reverse: reset to created_at (original backfill behavior)."""
    User = apps.get_model('helium_auth', 'User')
    User.objects.update(last_activity=F('created_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0040_user_deletion_warning_fields'),
    ]

    operations = [
        # First, fix the backfill data
        migrations.RunPython(fix_last_activity_backfill, reverse_fix),

        # Then alter the field to be non-nullable with auto_now_add
        migrations.AlterField(
            model_name='user',
            name='last_activity',
            field=models.DateTimeField(
                auto_now_add=True,
                db_index=True,
                help_text='Last user activity (login or token refresh).',
            ),
        ),
    ]
