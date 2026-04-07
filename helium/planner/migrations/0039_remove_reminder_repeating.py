# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0038_alter_reminder_start_of_range_nullable'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reminder',
            name='repeating',
        ),
    ]
