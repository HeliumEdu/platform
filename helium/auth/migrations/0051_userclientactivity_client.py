__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0050_tokenproxies'),
    ]

    operations = [
        migrations.AddField(
            model_name='userclientactivity',
            name='client',
            field=models.CharField(
                choices=[('mobile_app', 'Mobile App'), ('web', 'Web')],
                default='mobile_app',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='userclientactivity',
            unique_together={('user', 'date', 'client')},
        ),
    ]
