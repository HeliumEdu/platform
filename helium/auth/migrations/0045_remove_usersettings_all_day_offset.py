# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0044_usersettings_review_prompt_fields'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='usersettings',
            name='all_day_offset',
        ),
    ]
