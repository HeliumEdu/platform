from django.db import migrations, models


def convert_setup_flag_to_state(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')
    UserSettings.objects.filter(is_setup_complete=True).update(setup_state=2)


def convert_setup_state_to_flag(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')
    UserSettings.objects.filter(setup_state=2).update(is_setup_complete=True)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0072_usersettings_drop_year_first_date_format'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='setup_state',
            field=models.PositiveIntegerField(choices=[(0, 'Pending'), (1, 'Importing'), (2, 'Complete')], default=0, help_text="The account's progress through first-time setup."),
        ),
        migrations.RunPython(convert_setup_flag_to_state, convert_setup_state_to_flag),
        migrations.RemoveField(
            model_name='usersettings',
            name='is_setup_complete',
        ),
    ]
