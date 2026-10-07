from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0074_alter_usersettings_default_view'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='example_schedule_imported_at',
            field=models.DateTimeField(blank=True, help_text="When the example schedule last finished importing. Anything in it created or changed after this is the user's own work.", null=True),
        ),
    ]
