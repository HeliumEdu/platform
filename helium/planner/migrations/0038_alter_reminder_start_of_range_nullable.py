# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0037_homework_completed_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reminder',
            name='start_of_range',
            field=models.DateTimeField(db_index=True, null=True, blank=True),
        ),
    ]
