__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models


def deduplicate_push_tokens(apps, schema_editor):
    """
    Remove duplicate (user, device_id) push token rows, keeping the most
    recently updated one per pair. Must run before the unique constraint is
    applied so that existing prod data doesn't violate it.
    """
    UserPushToken = apps.get_model('helium_auth', 'UserPushToken')

    seen = set()
    # Order newest-first so the first occurrence we see is the keeper.
    for token in UserPushToken.objects.order_by('user_id', 'device_id', '-updated_at'):
        key = (token.user_id, token.device_id)
        if key in seen:
            token.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0046_usersettings_last_deletion_at'),
    ]

    operations = [
        migrations.RunPython(deduplicate_push_tokens, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name='userpushtoken',
            unique_together={('user', 'device_id')},
        ),
    ]
