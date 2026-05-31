__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('helium_auth', '0063_alter_useroauthprovider_created_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_power_user',
            field=models.BooleanField(
                default=False,
                help_text='True if this user is in the top 5% by composite engagement score (homework, completions, notes) '
                          'over the last 30 days. Recalculated nightly; cleared when the user drops out of the top 5%.'),
        ),
    ]
