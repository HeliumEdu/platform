# Generated manually

from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0040_reminder_attachment_exactly_one_parent'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='reminder',
            constraint=models.UniqueConstraint(
                fields=['course', 'user', 'type', 'offset', 'offset_type'],
                condition=Q(sent=False, dismissed=False),
                name='reminder_one_active_per_course_series',
            ),
        ),
    ]
