__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0050_alter_course_credits_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='recurrence_rule',
            field=models.CharField(blank=True, help_text='iCal RRULE string (e.g. `FREQ=WEEKLY;BYDAY=MO,WE,FR`) that turns this event into a recurring series anchored on `start`.', max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='exception_dates',
            field=models.JSONField(blank=True, help_text='List of ISO-8601 datetimes to skip when expanding `recurrence_rule` (iCal EXDATE).', null=True),
        ),
    ]
