# Generated manually

from django.db import migrations, models
from django.db.models import F


def seed_completed_at(apps, schema_editor):
    Homework = apps.get_model('planner', 'Homework')
    Homework.objects.filter(completed=True, completed_at__isnull=True).update(completed_at=F('updated_at'))


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0036_alter_reminder_dismissed'),
    ]

    operations = [
        migrations.AddField(
            model_name='homework',
            name='completed_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When the homework was first marked as completed. Set automatically.',
            ),
        ),
        migrations.RunPython(seed_completed_at, migrations.RunPython.noop),
    ]
