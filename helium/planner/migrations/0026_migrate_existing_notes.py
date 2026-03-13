__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import migrations


def migrate_notes_forward(apps, schema_editor):
    """Migrate existing inline notes to Note table.

    Title derivation: "Notes for: {Entity.title}"
    """
    Note = apps.get_model('planner', 'Note')
    NoteLink = apps.get_model('planner', 'NoteLink')
    Homework = apps.get_model('planner', 'Homework')
    Event = apps.get_model('planner', 'Event')
    Material = apps.get_model('planner', 'Material')

    # Migrate Homework notes
    for hw in Homework.objects.select_related('course__course_group').exclude(notes__isnull=True).exclude(notes={}):
        note = Note.objects.create(
            title=f'Notes for: {hw.title}',
            content=hw.notes,
            user_id=hw.course.course_group.user_id,
        )
        NoteLink.objects.create(note=note, homework=hw)

    # Migrate Event notes
    for ev in Event.objects.exclude(notes__isnull=True).exclude(notes={}):
        note = Note.objects.create(
            title=f'Notes for: {ev.title}',
            content=ev.notes,
            user_id=ev.user_id,
        )
        NoteLink.objects.create(note=note, event=ev)

    # Migrate Material notes
    for mat in Material.objects.select_related('material_group').exclude(notes__isnull=True).exclude(notes={}):
        note = Note.objects.create(
            title=f'Notes for: {mat.title}',
            content=mat.notes,
            user_id=mat.material_group.user_id,
        )
        NoteLink.objects.create(note=note, material=mat)


def migrate_notes_backward(apps, schema_editor):
    """Reverse: copy Note content back to inline fields and delete Note/NoteLink."""
    Note = apps.get_model('planner', 'Note')
    NoteLink = apps.get_model('planner', 'NoteLink')
    Homework = apps.get_model('planner', 'Homework')
    Event = apps.get_model('planner', 'Event')
    Material = apps.get_model('planner', 'Material')

    for link in NoteLink.objects.select_related('note', 'homework', 'event', 'material'):
        entity = link.homework or link.event or link.material
        if entity and hasattr(entity, 'notes'):
            entity.notes = link.note.content
            entity.save(update_fields=['notes'])

    # Delete all Notes (NoteLinks cascade)
    Note.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0025_note_tables'),
    ]

    operations = [
        migrations.RunPython(migrate_notes_forward, migrate_notes_backward),
    ]
