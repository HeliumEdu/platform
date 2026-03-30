# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0041_fix_last_activity_backfill'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='at_risk_threshold',
            field=models.PositiveIntegerField(
                default=70,
                help_text='The grade percentage below which a course is flagged as at-risk.',
            ),
        ),
    ]
