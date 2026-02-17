# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0035_set_existing_users_setup_complete'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='show_planner_tooltips',
            field=models.BooleanField(
                default=True,
                help_text='Whether planner item hover tooltips should be shown.',
            ),
        ),
    ]
