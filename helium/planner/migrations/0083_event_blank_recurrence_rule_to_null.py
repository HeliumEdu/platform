from django.db import migrations


def blank_recurrence_rule_to_null(apps, schema_editor):
    Event = apps.get_model('planner', 'Event')
    Event.objects.filter(recurrence_rule='').update(recurrence_rule=None)


class Migration(migrations.Migration):
    dependencies = [
        ('planner', '0082_homework_recurrence'),
    ]

    operations = [
        migrations.RunPython(blank_recurrence_rule_to_null, migrations.RunPython.noop),
    ]
