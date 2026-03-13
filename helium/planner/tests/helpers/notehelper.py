__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from helium.planner.models import Note, NoteLink


def given_note_exists(user, title='Test Note', content=None):
    note = Note.objects.create(
        title=title,
        content=content or {'ops': [{'insert': 'Test content\n'}]},
        user=user
    )
    return note


def given_note_linked_to_homework(user, homework, title=None, content=None):
    note = Note.objects.create(
        title=title or f'Notes for: {homework.title}',
        content=content or {'ops': [{'insert': 'Homework notes\n'}]},
        user=user
    )
    NoteLink.objects.create(note=note, homework=homework)
    return note


def given_note_linked_to_event(user, event, title=None, content=None):
    note = Note.objects.create(
        title=title or f'Notes for: {event.title}',
        content=content or {'ops': [{'insert': 'Event notes\n'}]},
        user=user
    )
    NoteLink.objects.create(note=note, event=event)
    return note


def given_note_linked_to_material(user, material, title=None, content=None):
    note = Note.objects.create(
        title=title or f'Notes for: {material.title}',
        content=content or {'ops': [{'insert': 'Material notes\n'}]},
        user=user
    )
    NoteLink.objects.create(note=note, material=material)
    return note


def verify_note_matches_data(test_case, note, data):
    test_case.assertEqual(note.title, data['title'])
    if 'content' in data and data['content']:
        test_case.assertEqual(note.content, data['content'])
