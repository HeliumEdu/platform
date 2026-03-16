__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from helium.planner.models import Note


def given_note_exists(user, title='Test Note', content=None):
    note = Note.objects.create(
        title=title,
        content=content or {'ops': [{'insert': 'Test content\n'}]},
        user=user
    )
    return note


def given_note_linked_to_homework(user, homework, title=None, content=None):
    note = Note.objects.create(
        title=title or '',
        content=content or {'ops': [{'insert': 'Homework notes\n'}]},
        user=user
    )
    note.homework.add(homework)
    return note


def given_note_linked_to_event(user, event, title=None, content=None):
    note = Note.objects.create(
        title=title or '',
        content=content or {'ops': [{'insert': 'Event notes\n'}]},
        user=user
    )
    note.events.add(event)
    return note


def given_note_linked_to_resource(user, resource, title=None, content=None):
    """Link a note to a resource (Material model)."""
    note = Note.objects.create(
        title=title or '',
        content=content or {'ops': [{'insert': 'Resource notes\n'}]},
        user=user
    )
    note.resources.add(resource)
    return note


def verify_note_matches_data(test_case, note, data):
    test_case.assertEqual(note.title, data['title'])
    if 'content' in data and data['content']:
        test_case.assertEqual(note.content, data['content'])
