__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0031_fix_list_newline_in_notes'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='example_schedule',
            field=models.BooleanField(default=False, help_text='Whether it is part of the example schedule.'),
        ),
    ]
