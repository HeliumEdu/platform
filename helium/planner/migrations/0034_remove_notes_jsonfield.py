__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations


class Migration(migrations.Migration):
    """Remove the `notes` JSONField from Event, Homework, and Material.

    The standalone Note model with M2M relationships is now the single source
    of truth for notes. The dual-write sync has been removed.
    """

    dependencies = [
        ('planner', '0033_note_m2m_refactor'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='notes',
        ),
        migrations.RemoveField(
            model_name='homework',
            name='notes',
        ),
        migrations.RemoveField(
            model_name='material',
            name='notes',
        ),
    ]
