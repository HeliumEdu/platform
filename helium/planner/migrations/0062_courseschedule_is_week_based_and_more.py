from django.db import migrations, models


def _backfill_is_week_based(apps, schema_editor):
    CourseSchedule = apps.get_model('planner', 'courseschedule')
    CourseSchedule.objects.filter(week_interval__isnull=False).update(is_week_based=True)


def _reverse_is_week_based(apps, schema_editor):
    CourseSchedule = apps.get_model('planner', 'courseschedule')
    CourseSchedule.objects.filter(is_week_based=True).update(week_interval=2)


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0061_courseschedule_anchor_date_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='courseschedule',
            name='cycle_length',
            field=models.PositiveSmallIntegerField(blank=True, help_text='The number of school days in one rotation cycle (mutually exclusive with `is_week_based`).', null=True),
        ),
        migrations.RemoveConstraint(
            model_name='courseschedule',
            name='courseschedule_single_rotation_type',
        ),
        migrations.AddField(
            model_name='courseschedule',
            name='is_week_based',
            field=models.BooleanField(default=False, help_text='Whether this is a week-based ("Week A/B") rotation, meeting every other week on the week matching `week_offset` (mutually exclusive with `cycle_length`).'),
        ),
        migrations.RunPython(_backfill_is_week_based, _reverse_is_week_based),
        migrations.RemoveField(
            model_name='courseschedule',
            name='week_interval',
        ),
        migrations.AddConstraint(
            model_name='courseschedule',
            constraint=models.CheckConstraint(condition=models.Q(('cycle_length__isnull', False), ('is_week_based', True), _negated=True), name='courseschedule_single_rotation_type'),
        ),
        migrations.AlterField(
            model_name='courseschedule',
            name='template',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Weekly'), (1, 'A/B Day'), (2, '6-Day Cycle'), (5, '7-Day Cycle'), (3, '8-Day Cycle'), (6, '10-Day Cycle'), (4, 'Week A/B')], help_text='The template this schedule was created from.', null=True),
        ),
    ]
