__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0048_alter_user_created_at_alter_user_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='mobile_app_usage_percent_30d',
            field=models.FloatField(
                blank=True,
                null=True,
                help_text='Percentage of the last 30 days the user was active on the mobile app. Updated nightly.',
            ),
        ),
        migrations.CreateModel(
            name='UserClientActivity',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='client_activity',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'unique_together': {('user', 'date')},
            },
        ),
    ]
