__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations


def remove_duplicate_linked_notes(apps, schema_editor):
    """
    Remove duplicate notes linked to the same entity, keeping only the newest.

    This cleans up data integrity issues where multiple notes were linked to
    the same homework, event, or resource before validation was added.
    """
    Note = apps.get_model('planner', 'Note')

    duplicates_removed = 0

    # Find homework with multiple linked notes
    from django.db.models import Count

    Homework = apps.get_model('planner', 'Homework')
    for hw in Homework.objects.annotate(note_count=Count('notes_set')).filter(note_count__gt=1):
        notes = list(Note.objects.filter(homework=hw).order_by('-updated_at'))
        # Keep the newest (first), delete the rest
        for note in notes[1:]:
            note.homework.remove(hw)
            # If note has no other links, delete it entirely
            if not note.homework.exists() and not note.events.exists() and not note.resources.exists():
                note.delete()
            duplicates_removed += 1

    # Find events with multiple linked notes
    Event = apps.get_model('planner', 'Event')
    for event in Event.objects.annotate(note_count=Count('notes_set')).filter(note_count__gt=1):
        notes = list(Note.objects.filter(events=event).order_by('-updated_at'))
        for note in notes[1:]:
            note.events.remove(event)
            if not note.homework.exists() and not note.events.exists() and not note.resources.exists():
                note.delete()
            duplicates_removed += 1

    # Find resources (Material) with multiple linked notes
    Material = apps.get_model('planner', 'Material')
    for material in Material.objects.annotate(note_count=Count('notes_set')).filter(note_count__gt=1):
        notes = list(Note.objects.filter(resources=material).order_by('-updated_at'))
        for note in notes[1:]:
            note.resources.remove(material)
            if not note.homework.exists() and not note.events.exists() and not note.resources.exists():
                note.delete()
            duplicates_removed += 1

    if duplicates_removed > 0:
        print(f"\n  Removed {duplicates_removed} duplicate note link(s)")


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0034_remove_notes_jsonfield'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_linked_notes, migrations.RunPython.noop),
    ]
