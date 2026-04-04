# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0045_remove_usersettings_all_day_offset'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='last_deletion_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
