__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Note
from helium.planner.tests.helpers import (
    notehelper, eventhelper, homeworkhelper, coursegrouphelper, coursehelper,
    materialgrouphelper, materialhelper
)


class TestCaseNoteViews(APITestCase):
    def test_note_login_required(self):
        userhelper.given_a_user_exists()
        responses = [
            self.client.get(reverse('planner_notes_list')),
            self.client.post(reverse('planner_notes_list')),
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': '9999'}))
        ]
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_notes(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user2)
        notehelper.given_note_exists(user2)
        response = self.client.get(reverse('planner_notes_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Note.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        data = {
            'title': 'My Test Note',
            'content': {'ops': [{'insert': 'Some content here\n'}]}
        }
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Note.objects.count(), 1)
        note = Note.objects.get(pk=response.data['id'])
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.content, data['content'])
        self.assertEqual(note.user, user)

    def test_create_standalone_note(self):
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        data = {
            'title': 'Standalone Note',
            'content': {'ops': [{'insert': 'Just a note\n'}]}
        }
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps(data),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        note = Note.objects.get(pk=response.data['id'])
        self.assertFalse(note.has_linked_entity())

    def test_get_note_by_id(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], note.pk)
        self.assertEqual(response.data['title'], note.title)

    def test_get_note_includes_link_info(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['linked_entity_type'], 'event')
        self.assertEqual(response.data['linked_entity_title'], event.title)
        self.assertIn(event.pk, response.data['events'])

    def test_update_note_by_id(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)
        data = {
            'title': 'Updated Title',
            'content': {'ops': [{'insert': 'Updated content\n'}]}
        }
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.content, data['content'])

    def test_patch_note_by_id(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user, title='Original Title')
        data = {'title': 'Patched Title'}
        response = self.client.patch(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                     json.dumps(data),
                                     content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, 'Patched Title')

    def test_delete_note_by_id(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)
        response = self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_no_access_object_owned_by_another_user(self):
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        note = notehelper.given_note_exists(user1)
        responses = [
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        ]
        self.assertTrue(Note.objects.filter(pk=note.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        responses = [
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': '9999'}))
        ]
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_title_search_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user, title='Unique Search Title')
        notehelper.given_note_exists(user, title='Other Note')
        response = self.client.get(reverse('planner_notes_list') + '?search=UniQue')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], note.title)

    def test_filter_by_linked_entity_type(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note_with_event = notehelper.given_note_linked_to_event(user, event)
        notehelper.given_note_exists(user, title='Standalone')
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=event')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], note_with_event.pk)

    def test_filter_standalone_notes(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        notehelper.given_note_linked_to_event(user, event)
        standalone = notehelper.given_note_exists(user, title='Standalone')
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=standalone')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], standalone.pk)

    def test_updated_at_filter(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note1 = notehelper.given_note_exists(user, title='Old')
        note2 = notehelper.given_note_exists(user, title='Recent')
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Note.objects.filter(pk=note1.pk).update(updated_at=old_time)
        Note.objects.filter(pk=note2.pk).update(updated_at=recent_time)
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(reverse('planner_notes_list') + f'?updated_at__gte={filter_time}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], note2.pk)


class TestCaseNoteExtendedFields(APITestCase):
    def test_update_standalone_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)
        new_content = {'ops': [{'insert': 'Updated standalone\n'}]}
        data = {'title': note.title, 'content': new_content}
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.content, new_content)

    def test_get_note_includes_colors_for_homework(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['linked_entity_type'], 'homework')
        self.assertEqual(response.data['course_color'], course.color)

    def test_get_note_includes_link_info_with_resource(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_linked_to_resource(user, resource)
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['linked_entity_type'], 'resource')
        self.assertEqual(response.data['linked_entity_title'], resource.title)

    def test_ordering_by_title(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(user, title='Zebra')
        notehelper.given_note_exists(user, title='Apple')
        notehelper.given_note_exists(user, title='Mango')
        response = self.client.get(reverse('planner_notes_list') + '?ordering=title')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['title'], 'Apple')
        self.assertEqual(response.data[1]['title'], 'Mango')
        self.assertEqual(response.data[2]['title'], 'Zebra')

    def test_list_excludes_content(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(user, content={'ops': [{'insert': 'Large content\n'}]})
        response = self.client.get(reverse('planner_notes_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn('content', response.data[0])

    def test_detail_includes_content(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        content = {'ops': [{'insert': 'Detailed content\n'}]}
        note = notehelper.given_note_exists(user, content=content)
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('content', response.data)
        self.assertEqual(response.data['content'], content)

class TestCaseNoteEdgeCases(APITestCase):
    def test_delete_entity_deletes_linked_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        note_pk = note.pk
        response = self.client.delete(reverse('planner_events_detail', kwargs={'pk': event.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_clear_note_content_via_note_api_deletes_linked_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(
            user, event, content={'ops': [{'insert': 'Some notes\n'}]}
        )
        note_pk = note.pk
        self.assertTrue(Note.objects.filter(pk=note_pk).exists())
        data = {'content': {}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note_pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_clear_note_content_standalone_note_not_deleted(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(
            user, title='Standalone', content={'ops': [{'insert': 'Some content\n'}]}
        )
        note_pk = note.pk
        self.assertFalse(note.has_linked_entity())
        data = {'content': {}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note_pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Note.objects.filter(pk=note_pk).exists())
        note.refresh_from_db()
        self.assertEqual(note.content, {})


class TestCaseNoteValidation(APITestCase):
    def test_note_rejects_multiple_link_types(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_exists(user)
        data = {
            'title': note.title,
            'content': note.content,
            'homework': [homework.pk],
            'events': [event.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one type', str(response.data))

    def test_note_rejects_multiple_items_of_same_type(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event1 = eventhelper.given_event_exists(user)
        event2 = eventhelper.given_event_exists(user)
        note = notehelper.given_note_exists(user)
        data = {
            'title': note.title,
            'content': note.content,
            'events': [event1.pk, event2.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one event', str(response.data))

    def test_note_rejects_multiple_homework(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        hw1 = homeworkhelper.given_homework_exists(course)
        hw2 = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_exists(user)
        data = {
            'title': note.title,
            'content': note.content,
            'homework': [hw1.pk, hw2.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one homework', str(response.data))

    def test_note_rejects_multiple_resources(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource1 = materialhelper.given_material_exists(material_group)
        resource2 = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_exists(user)
        data = {
            'title': note.title,
            'content': note.content,
            'resources': [resource1.pk, resource2.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one resource', str(response.data))

    def test_note_rejects_linking_to_homework_with_existing_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        notehelper.given_note_linked_to_homework(user, homework)
        new_note = notehelper.given_note_exists(user)
        data = {
            'title': new_note.title,
            'content': new_note.content,
            'homework': [homework.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': new_note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has a linked note', str(response.data))

    def test_note_rejects_linking_to_event_with_existing_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        notehelper.given_note_linked_to_event(user, event)
        new_note = notehelper.given_note_exists(user)
        data = {
            'title': new_note.title,
            'content': new_note.content,
            'events': [event.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': new_note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has a linked note', str(response.data))

    def test_note_rejects_linking_to_resource_with_existing_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        notehelper.given_note_linked_to_resource(user, resource)
        new_note = notehelper.given_note_exists(user)
        data = {
            'title': new_note.title,
            'content': new_note.content,
            'resources': [resource.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': new_note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('already has a linked note', str(response.data))

    def test_note_allows_update_own_link(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        data = {
            'title': 'Updated Title',
            'content': {'ops': [{'insert': 'Updated content\n'}]},
            'events': [event.pk],
        }
        response = self.client.put(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, 'Updated Title')
