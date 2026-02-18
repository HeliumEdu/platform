# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0036_usersettings_show_planner_tooltips'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='drag_and_drop_on_mobile',
            field=models.BooleanField(
                default=True,
                help_text='Whether drag-and-drop is enabled on touch/mobile devices.',
            ),
        ),
    ]
