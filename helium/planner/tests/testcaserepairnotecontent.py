import importlib

from django.apps import apps
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import notehelper

migration = importlib.import_module('helium.planner.migrations.0077_repair_note_content')


class TestCaseRepairNoteContent(TestCase):
    def test_keeps_the_text_of_a_note_holding_change_ops(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, content={'ops': [
            {'insert': 'Lecture 4\n', 'attributes': {'header': 1}},
            {'retain': 3, 'attributes': {'bold': True}},
            {'insert': 'Mitochondria\n'},
            {'delete': 2},
        ]})

        # WHEN
        migration.repair_note_content(apps, None)

        # THEN
        note.refresh_from_db()
        self.assertEqual(note.content, {'ops': [
            {'insert': 'Lecture 4\n', 'attributes': {'header': 1}},
            {'insert': 'Mitochondria\n'},
        ]})

    def test_a_note_left_with_no_inserts_becomes_an_empty_document(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, content={'ops': [{'retain': 5}]})

        # WHEN
        migration.repair_note_content(apps, None)

        # THEN
        note.refresh_from_db()
        self.assertEqual(note.content, {'ops': [{'insert': '\n'}]})

    def test_leaves_valid_notes_untouched(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        valid = {'ops': [{'insert': 'Fine\n', 'attributes': {'italic': True}}]}
        note = notehelper.given_note_exists(user, content=valid)
        before = note.updated_at

        # WHEN
        migration.repair_note_content(apps, None)

        # THEN
        note.refresh_from_db()
        self.assertEqual(note.content, valid)
        self.assertEqual(note.updated_at, before)
