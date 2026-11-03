import re

from django.db import migrations

from helium.planner.utils.quillutils import html_to_quill, plain_text_to_quill

_HTML_TAG = re.compile(r'<[a-zA-Z/!][^>]*>')


def _to_quill(text):
    content = html_to_quill(text) if _HTML_TAG.search(text) else None
    return content or plain_text_to_quill(text)


def _move_to_notes(Note, rows, text_field, note_field, owner_and_example):
    for row in rows.exclude(**{text_field: ''}).filter(notes_set__isnull=True).iterator():
        content = _to_quill(getattr(row, text_field))
        if not content:
            continue
        user_id, example_schedule = owner_and_example(row)
        note = Note.objects.create(title='', content=content, user_id=user_id, example_schedule=example_schedule)
        getattr(note, note_field).add(row)


def move_unlinked_text_to_notes(apps, schema_editor):
    """
    Give every Assignment, Event and Resource that still holds `comments` / `details` text, and has no
    linked Note, a Note carrying that text before the columns are dropped. Migration 0027 converted
    everything up to its release; this catches what was written since (.ics imports, older clients).
    """
    Note = apps.get_model('planner', 'Note')
    Homework = apps.get_model('planner', 'Homework')
    Event = apps.get_model('planner', 'Event')
    Material = apps.get_model('planner', 'Material')

    _move_to_notes(Note, Homework.objects.select_related('course__course_group'), 'comments', 'homework',
                   lambda hw: (hw.course.course_group.user_id, hw.course.course_group.example_schedule))
    _move_to_notes(Note, Event.objects.all(), 'comments', 'events',
                   lambda ev: (ev.user_id, ev.example_schedule))
    _move_to_notes(Note, Material.objects.select_related('material_group'), 'details', 'resources',
                   lambda mat: (mat.material_group.user_id, mat.material_group.example_schedule))


class Migration(migrations.Migration):

    dependencies = [
        ('planner', '0073_alter_category_weight_alter_homework_completed'),
    ]

    operations = [
        migrations.RunPython(move_unlinked_text_to_notes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='event',
            name='comments',
        ),
        migrations.RemoveField(
            model_name='homework',
            name='comments',
        ),
        migrations.RemoveField(
            model_name='material',
            name='details',
        ),
    ]
