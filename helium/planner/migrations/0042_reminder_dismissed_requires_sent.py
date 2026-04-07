# Generated manually

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0041_reminder_one_active_per_course_series'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reminder',
            constraint=models.CheckConstraint(
                check=Q(dismissed=False) | Q(sent=True),
                name='reminder_dismissed_requires_sent',
            ),
        ),
    ]
