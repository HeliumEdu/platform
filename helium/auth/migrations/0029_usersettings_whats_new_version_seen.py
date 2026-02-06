# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0028_usersettings_color_scheme_theme'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='whats_new_version_seen',
            field=models.PositiveIntegerField(default=0, help_text='The "What\'s New" dialog version the user has seen.'),
        ),
    ]
