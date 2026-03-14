__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations


def strip_notes_for_prefix_forward(apps, schema_editor):
    """Strip the 'Notes for: ' prefix from all Note titles."""
    Note = apps.get_model('planner', 'Note')

    notes = Note.objects.filter(title__startswith='Notes for: ')
    for note in notes:
        note.title = note.title[len('Notes for: '):]
        note.save(update_fields=['title'])


def strip_notes_for_prefix_backward(apps, schema_editor):
    """Re-add 'Notes for: ' prefix — not feasible to restore original titles, so this is a no-op."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0027_migrate_all_legacy_notes'),
    ]

    operations = [
        migrations.RunPython(strip_notes_for_prefix_forward, strip_notes_for_prefix_backward),
    ]
