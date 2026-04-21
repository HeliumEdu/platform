# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0054_fix_dark_theme_default'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='onboarding_completed_at',
            field=models.DateTimeField(
                blank=True, null=True,
                help_text='When the user first cleared the example schedule (end of onboarding). '
                          'Write-once: set on the first successful clear and never updated afterward.',
            ),
        ),
    ]
