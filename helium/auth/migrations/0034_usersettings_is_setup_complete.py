# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0033_remove_useroauthprovider_unique_user_provider_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='usersettings',
            name='is_setup_complete',
            field=models.BooleanField(default=False, help_text='Whether the account setup is complete (example schedule imported).'),
        ),
    ]
