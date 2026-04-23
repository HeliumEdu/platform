# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0055_user_onboarding_completed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='deletion_requested_at',
            field=models.DateTimeField(
                blank=True, null=True, db_index=True,
                help_text='When the user requested account deletion. Non-null means the account is '
                          'pending async cascade-delete: login/OAuth/verification paths treat the user '
                          'as not-found, but the email/username remain reserved so new signups collide.',
            ),
        ),
    ]
