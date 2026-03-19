__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Note
from helium.planner.tests.helpers import (
    coursegrouphelper, coursehelper, homeworkhelper, eventhelper,
    materialgrouphelper, materialhelper, notehelper
)


class TestCaseNote(TestCase):
    def test_note_creation(self):
        user = userhelper.given_a_user_exists()
        note = Note.objects.create(
            title='Test Note',
            content={'ops': [{'insert': 'Hello\n'}]},
            user=user
        )
        self.assertEqual(note.title, 'Test Note')
        self.assertEqual(note.user, user)
        self.assertIsNotNone(note.created_at)
        self.assertIsNotNone(note.updated_at)

    def test_note_str(self):
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, title='My Note')
        self.assertIn('My Note', str(note))
        self.assertIn(user.get_username(), str(note))

    def test_note_str_untitled(self):
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user, title='')
        self.assertIn('Untitled', str(note))

    def test_note_get_user(self):
        user = userhelper.given_a_user_exists()
        note = notehelper.given_note_exists(user)
        self.assertEqual(note.get_user(), user)

    def test_note_manager_for_user(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists(username='user2', email='user2@test.com')
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user2)
        self.assertEqual(Note.objects.for_user(user1.pk).count(), 2)
        self.assertEqual(Note.objects.for_user(user2.pk).count(), 1)

    def test_note_manager_exists_for_user(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists(username='user2', email='user2@test.com')
        note = notehelper.given_note_exists(user1)
        self.assertTrue(Note.objects.exists_for_user(note.pk, user1.pk))
        self.assertFalse(Note.objects.exists_for_user(note.pk, user2.pk))


class TestCaseNoteLinks(TestCase):
    def test_note_linked_to_homework(self):
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)
        self.assertEqual(note.linked_entity, homework)
        self.assertEqual(note.linked_entity_type, 'homework')
        self.assertEqual(note.linked_entity_title, homework.title)
        self.assertEqual(note.course_color, course.color)

    def test_note_linked_to_event(self):
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        self.assertEqual(note.linked_entity, event)
        self.assertEqual(note.linked_entity_type, 'event')
        self.assertEqual(note.linked_entity_title, event.title)
        self.assertIsNone(note.course_color)

    def test_note_linked_to_resource(self):
        user = userhelper.given_a_user_exists()
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_linked_to_resource(user, resource)
        self.assertEqual(note.linked_entity, resource)
        self.assertEqual(note.linked_entity_type, 'resource')
        self.assertEqual(note.linked_entity_title, resource.title)
        self.assertIsNone(note.course_color)

    def test_delete_entity_cascades_to_note(self):
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        note_pk = note.pk
        event.delete()
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_delete_homework_cascades_to_note(self):
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)
        note_pk = note.pk
        homework.delete()
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_delete_resource_cascades_to_note(self):
        user = userhelper.given_a_user_exists()
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_linked_to_resource(user, resource)
        note_pk = note.pk
        resource.delete()
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_has_linked_entity(self):
        user = userhelper.given_a_user_exists()
        standalone = notehelper.given_note_exists(user)
        self.assertFalse(standalone.has_linked_entity())
        event = eventhelper.given_event_exists(user)
        linked = notehelper.given_note_linked_to_event(user, event)
        self.assertTrue(linked.has_linked_entity())
