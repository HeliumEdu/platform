# Generated manually

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0039_remove_reminder_repeating'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reminder',
            constraint=models.CheckConstraint(
                check=(
                    Q(homework__isnull=False, event__isnull=True, course__isnull=True) |
                    Q(homework__isnull=True, event__isnull=False, course__isnull=True) |
                    Q(homework__isnull=True, event__isnull=True, course__isnull=False)
                ),
                name='reminder_exactly_one_parent',
            ),
        ),
        migrations.AddConstraint(
            model_name='attachment',
            constraint=models.CheckConstraint(
                check=(
                    Q(homework__isnull=False, event__isnull=True, course__isnull=True) |
                    Q(homework__isnull=True, event__isnull=False, course__isnull=True) |
                    Q(homework__isnull=True, event__isnull=True, course__isnull=False)
                ),
                name='attachment_exactly_one_parent',
            ),
        ),
    ]
