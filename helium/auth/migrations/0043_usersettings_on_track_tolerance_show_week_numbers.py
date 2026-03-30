# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0042_usersettings_at_risk_threshold'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='on_track_tolerance',
            field=models.PositiveIntegerField(
                default=10,
                help_text='The percentage tolerance within which a course grade is considered on track.',
            ),
        ),
        migrations.AddField(
            model_name='usersettings',
            name='show_week_numbers',
            field=models.BooleanField(
                default=True,
                help_text='Whether week numbers should be shown on the calendar.',
            ),
        ),
    ]
