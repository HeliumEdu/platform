__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailReputationEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('email', models.EmailField(db_index=True, max_length=254)),
                ('email_type', models.CharField(
                    choices=[
                        ('verification', 'Verification'),
                        ('registration', 'Registration'),
                        ('password_reset', 'Password Reset'),
                        ('dormant_warning', 'Dormant Warning'),
                        ('reminder', 'Reminder'),
                        ('unknown', 'Unknown'),
                    ],
                    default='unknown',
                    max_length=50,
                )),
                ('event_type', models.CharField(
                    choices=[('bounce', 'Bounce'), ('complaint', 'Complaint')],
                    max_length=20,
                )),
                ('event_subtype', models.CharField(blank=True, max_length=50, null=True)),
                ('sns_message_id', models.CharField(max_length=100, unique=True)),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='email_reputation_events',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='emailreputationevent',
            index=models.Index(fields=['email', 'event_type'], name='helium_comm_email_event_type_idx'),
        ),
    ]
