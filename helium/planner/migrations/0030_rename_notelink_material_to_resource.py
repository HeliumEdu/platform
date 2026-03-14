__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0029_strip_notes_for_prefix_again'),
    ]

    operations = [
        # Remove the old constraint first
        migrations.RemoveConstraint(
            model_name='notelink',
            name='notelink_exactly_one_entity',
        ),
        # Rename the field from material to resource
        migrations.RenameField(
            model_name='notelink',
            old_name='material',
            new_name='resource',
        ),
        # Re-add the constraint with the new field name
        migrations.AddConstraint(
            model_name='notelink',
            constraint=models.CheckConstraint(
                check=(
                    Q(homework__isnull=False, event__isnull=True, resource__isnull=True) |
                    Q(homework__isnull=True, event__isnull=False, resource__isnull=True) |
                    Q(homework__isnull=True, event__isnull=True, resource__isnull=False)
                ),
                name='notelink_exactly_one_entity',
            ),
        ),
    ]
