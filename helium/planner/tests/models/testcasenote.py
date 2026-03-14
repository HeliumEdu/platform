__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.db import IntegrityError
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Note, NoteLink
from helium.planner.tests.helpers import (
    coursegrouphelper, coursehelper, homeworkhelper, eventhelper,
    materialgrouphelper, materialhelper, notehelper
)


class TestCaseNote(TestCase):
    def test_note_creation(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        note = Note.objects.create(
            title='Test Note',
            content={'ops': [{'insert': 'Hello\n'}]},
            user=user
        )

        # THEN
        self.assertEqual(note.title, 'Test Note')
        self.assertEqual(note.user, user)
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)

    def test_note_str(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, title='My Note')

        # THEN
        self.assertIn('My Note', str(note))
        self.assertIn(user.get_username(), str(note))

    def test_note_str_untitled(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, title='')

        # THEN
        self.assertIn('Untitled', str(note))

    def test_note_get_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user)

        # THEN
        self.assertEqual(note.get_user(), user)

    def test_note_manager_for_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists(username='user2', email='user2@test.com')
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user2)

        # THEN
        self.assertEqual(Note.objects.for_user(user1.pk).count(), 2)
        self.assertEqual(Note.objects.for_user(user2.pk).count(), 1)

    def test_note_manager_exists_for_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists(username='user2', email='user2@test.com')
        note = notehelper.given_note_exists(user1)

        # THEN
        self.assertTrue(Note.objects.exists_for_user(note.pk, user1.pk))
        self.assertFalse(Note.objects.exists_for_user(note.pk, user2.pk))


class TestCaseNoteLink(TestCase):
    def test_notelink_to_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_exists(user)

        # WHEN
        link = NoteLink.objects.create(note=note, homework=homework)

        # THEN
        self.assertEqual(link.linked_entity, homework)
        self.assertEqual(link.linked_entity_type, 'homework')
        self.assertEqual(link.linked_entity_title, homework.title)
        self.assertEqual(link.linked_entity_color, course.color)

    def test_notelink_to_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)

        # WHEN
        link = NoteLink.objects.create(note=note, event=event)

        # THEN
        self.assertEqual(link.linked_entity, event)
        self.assertEqual(link.linked_entity_type, 'event')
        self.assertEqual(link.linked_entity_title, event.title)
        self.assertIsNone(link.linked_entity_color)

    def test_notelink_to_material(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_exists(user)

        # WHEN
        link = NoteLink.objects.create(note=note, material=material)

        # THEN
        self.assertEqual(link.linked_entity, material)
        self.assertEqual(link.linked_entity_type, 'material')
        self.assertEqual(link.linked_entity_title, material.title)
        self.assertIsNone(link.linked_entity_color)

    def test_notelink_str_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, event=event)

        # THEN
        self.assertIn(str(note.id), str(link))
        self.assertIn('Event', str(link))

    def test_notelink_str_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, homework=homework)

        # THEN
        self.assertIn(str(note.id), str(link))
        self.assertIn('Homework', str(link))

    def test_notelink_str_material(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, material=material)

        # THEN
        self.assertIn(str(note.id), str(link))
        self.assertIn('Material', str(link))

    def test_notelink_get_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, event=event)

        # THEN
        self.assertEqual(link.get_user(), user)

    def test_notelink_constraint_requires_one_entity(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user)

        # WHEN/THEN - Creating a link with no entity should fail
        with self.assertRaises(IntegrityError):
            NoteLink.objects.create(note=note)

    def test_notelink_constraint_allows_only_one_entity(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_exists(user)

        # WHEN/THEN - Creating a link with multiple entities should fail
        with self.assertRaises(IntegrityError):
            NoteLink.objects.create(note=note, event=event, homework=homework)

    def test_delete_entity_cascades_to_notelink(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, event=event)
        link_pk = link.pk

        # WHEN
        event.delete()

        # THEN
        self.assertFalse(NoteLink.objects.filter(pk=link_pk).exists())
        self.assertTrue(Note.objects.filter(pk=note.pk).exists())  # Note still exists

    def test_delete_note_cascades_to_notelink(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)
        link = NoteLink.objects.create(note=note, event=event)
        link_pk = link.pk

        # WHEN
        note.delete()

        # THEN
        self.assertFalse(NoteLink.objects.filter(pk=link_pk).exists())
        self.assertTrue(event.__class__.objects.filter(pk=event.pk).exists())  # Event still exists
