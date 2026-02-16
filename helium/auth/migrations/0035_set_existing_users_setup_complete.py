# Generated manually

from django.db import migrations


def set_existing_users_setup_complete(apps, schema_editor):
    """Set is_setup_complete=True for all existing users."""
    UserSettings = apps.get_model('helium_auth', 'UserSettings')
    UserSettings.objects.all().update(is_setup_complete=True)


def reverse_set_existing_users_setup_complete(apps, schema_editor):
    """Reverse: set is_setup_complete=False for all users."""
    UserSettings = apps.get_model('helium_auth', 'UserSettings')
    UserSettings.objects.all().update(is_setup_complete=False)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0034_usersettings_is_setup_complete'),
    ]

    operations = [
        migrations.RunPython(
            set_existing_users_setup_complete,
            reverse_set_existing_users_setup_complete,
        ),
    ]
