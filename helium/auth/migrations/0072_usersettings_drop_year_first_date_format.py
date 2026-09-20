from django.db import migrations, models


def move_year_first_to_day_first(apps, schema_editor):
    UserSettings = apps.get_model('helium_auth', 'UserSettings')
    UserSettings.objects.filter(date_format=2).update(date_format=1)


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0071_usersettings_regional_formats'),
    ]

    operations = [
        migrations.RunPython(move_year_first_to_day_first, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usersettings',
            name='date_format',
            field=models.PositiveIntegerField(choices=[(0, 'Month/Day/Year'), (1, 'Day/Month/Year')], default=0, help_text='The order in which day, month, and year are shown in dates.'),
        ),
    ]
