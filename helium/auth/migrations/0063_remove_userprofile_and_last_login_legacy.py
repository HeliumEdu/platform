__copyright__ = "Copyright (c) 2026 Helium Edu"
__license__ = "MIT"

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0062_alter_usersettings_default_reminder_type'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='last_login_legacy',
        ),
        migrations.DeleteModel(
            name='UserProfile',
        ),
    ]
