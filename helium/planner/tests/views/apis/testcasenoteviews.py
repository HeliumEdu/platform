__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Note, NoteLink
from helium.planner.tests.helpers import (
    notehelper, eventhelper, homeworkhelper, coursegrouphelper, coursehelper,
    materialgrouphelper, materialhelper
)


class TestCaseNoteViews(APITestCase):
    def test_note_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_notes_list')),
            self.client.post(reverse('planner_notes_list')),
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_notes(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        notehelper.given_note_exists(user1)
        notehelper.given_note_exists(user2)
        notehelper.given_note_exists(user2)

        # WHEN
        response = self.client.get(reverse('planner_notes_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Note.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'My Test Note',
            'content': {'ops': [{'insert': 'Some content here\n'}]}
        }
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Note.objects.count(), 1)
        note = Note.objects.get(pk=response.data['id'])
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.content, data['content'])
        self.assertEqual(note.user, user)

    def test_create_standalone_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Standalone Note',
            'content': {'ops': [{'insert': 'Just a note\n'}]}
        }
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        note = Note.objects.get(pk=response.data['id'])
        self.assertEqual(note.links.count(), 0)  # No links = standalone

    def test_get_note_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)

        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], note.pk)
        self.assertEqual(response.data['title'], note.title)

    def test_get_note_includes_link_info(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)

        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('link', response.data)
        self.assertEqual(response.data['link']['event'], event.pk)
        self.assertEqual(response.data['link']['linked_entity_type'], 'event')
        self.assertEqual(response.data['link']['linked_entity_title'], event.title)

    def test_update_note_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)

        # WHEN
        data = {
            'title': 'Updated Title',
            'content': {'ops': [{'insert': 'Updated content\n'}]}
        }
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, data['title'])
        self.assertEqual(note.content, data['content'])

    def test_patch_note_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user, title='Original Title')

        # WHEN
        data = {'title': 'Patched Title'}
        response = self.client.patch(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, 'Patched Title')

    def test_delete_note_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)

        # WHEN
        response = self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

    def test_delete_note_cascades_to_links(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        link_pk = note.links.first().pk

        # WHEN
        response = self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(NoteLink.objects.filter(pk=link_pk).exists())

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        note = notehelper.given_note_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        ]

        # THEN
        self.assertTrue(Note.objects.filter(pk=note.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_not_found(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        responses = [
            self.client.get(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_notes_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_notes_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_title_search_query(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user, title='Unique Search Title')
        notehelper.given_note_exists(user, title='Other Note')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=UniQue')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], note.title)

    def test_filter_by_linked_entity_type(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note_with_event = notehelper.given_note_linked_to_event(user, event)
        notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=event')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], note_with_event.pk)

    def test_filter_standalone_notes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        notehelper.given_note_linked_to_event(user, event)
        standalone = notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=standalone')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], standalone.pk)

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note1 = notehelper.given_note_exists(user, title='Old')
        note2 = notehelper.given_note_exists(user, title='Recent')

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Note.objects.filter(pk=note1.pk).update(updated_at=old_time)
        Note.objects.filter(pk=note2.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(reverse('planner_notes_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], note2.pk)


class TestCaseNoteDualWrite(APITestCase):
    """Test dual-write functionality for legacy frontend compatibility."""

    def test_update_note_syncs_to_linked_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)

        # WHEN
        new_content = {'ops': [{'insert': 'Updated via Note API\n'}]}
        data = {'title': note.title, 'content': new_content}
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        homework.refresh_from_db()
        self.assertEqual(homework.notes, new_content)

    def test_update_note_syncs_to_linked_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)

        # WHEN
        new_content = {'ops': [{'insert': 'Updated via Note API\n'}]}
        data = {'title': note.title, 'content': new_content}
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.notes, new_content)

    def test_patch_note_content_syncs_to_linked_entity(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)

        # WHEN
        new_content = {'ops': [{'insert': 'Patched content\n'}]}
        data = {'content': new_content}
        response = self.client.patch(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.notes, new_content)

    def test_update_standalone_note_no_sync(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(user)  # Standalone, no links

        # WHEN
        new_content = {'ops': [{'insert': 'Updated standalone\n'}]}
        data = {'title': note.title, 'content': new_content}
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.content, new_content)

    def test_update_note_syncs_to_linked_resource(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_linked_to_resource(user, resource)

        # WHEN
        new_content = {'ops': [{'insert': 'Updated via Note API\n'}]}
        data = {'title': note.title, 'content': new_content}
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': note.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resource.refresh_from_db()
        self.assertEqual(resource.notes, new_content)

    def test_get_note_includes_link_info_with_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        note = notehelper.given_note_linked_to_homework(user, homework)

        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('link', response.data)
        self.assertEqual(response.data['link']['homework'], homework.pk)
        self.assertEqual(response.data['link']['linked_entity_type'], 'homework')
        self.assertEqual(response.data['link']['linked_entity_title'], homework.title)
        self.assertEqual(response.data['link']['linked_entity_color'], course.color)

    def test_get_note_includes_link_info_with_resource(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        resource = materialhelper.given_material_exists(material_group)
        note = notehelper.given_note_linked_to_resource(user, resource)

        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('link', response.data)
        self.assertEqual(response.data['link']['resource'], resource.pk)
        self.assertEqual(response.data['link']['linked_entity_type'], 'resource')
        self.assertEqual(response.data['link']['linked_entity_title'], resource.title)

    def test_ordering_by_title(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(user, title='Zebra')
        notehelper.given_note_exists(user, title='Apple')
        notehelper.given_note_exists(user, title='Mango')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?ordering=title')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['title'], 'Apple')
        self.assertEqual(response.data[1]['title'], 'Mango')
        self.assertEqual(response.data[2]['title'], 'Zebra')

    def test_ordering_by_title_descending(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(user, title='Zebra')
        notehelper.given_note_exists(user, title='Apple')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?ordering=-title')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['title'], 'Zebra')
        self.assertEqual(response.data[1]['title'], 'Apple')

    def test_list_excludes_content(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(user, content={'ops': [{'insert': 'Large content\n'}]})

        # WHEN
        response = self.client.get(reverse('planner_notes_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertNotIn('content', response.data[0])

    def test_detail_includes_content(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        content = {'ops': [{'insert': 'Detailed content\n'}]}
        note = notehelper.given_note_exists(user, content=content)

        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('content', response.data)
        self.assertEqual(response.data['content'], content)

    def test_delete_note_clears_linked_entity_notes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        event.notes = {'ops': [{'insert': 'Event notes\n'}]}
        event.save()
        note = notehelper.given_note_linked_to_event(user, event, content=event.notes)

        # WHEN - Delete the note via API
        response = self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        event.refresh_from_db()
        self.assertIsNone(event.notes)

    def test_delete_note_then_recreate_via_entity(self):
        """
        Test flow:
        1. Create event with notes -> Note entity created
        2. Delete the Note via API -> Event.notes cleared
        3. Fetch event -> notes is empty
        4. Update event with new notes -> new Note entity created
        """
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # Step 1: Create note via event
        notes_content_v1 = {'ops': [{'insert': 'Original notes\n'}]}
        data = {
            'title': event.title,
            'all_day': event.all_day,
            'show_end_time': event.show_end_time,
            'start': event.start.isoformat(),
            'end': event.end.isoformat(),
            'priority': event.priority,
            'notes': notes_content_v1,
        }
        response = self.client.put(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify Note was created
        event.refresh_from_db()
        self.assertTrue(event.note_links.exists())
        note_v1 = event.note_links.first().note
        note_v1_pk = note_v1.pk
        self.assertEqual(note_v1.content, notes_content_v1)

        # Step 2: Delete the Note via API
        response = self.client.delete(reverse('planner_notes_detail', kwargs={'pk': note_v1_pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Step 3: Verify event.notes is cleared
        event.refresh_from_db()
        self.assertIsNone(event.notes)
        self.assertFalse(event.note_links.exists())

        # Fetch event via API and verify notes is empty
        response = self.client.get(reverse('planner_events_detail', kwargs={'pk': event.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data.get('notes'))

        # Step 4: Save event with new notes
        notes_content_v2 = {'ops': [{'insert': 'New notes after deletion\n'}]}
        data['notes'] = notes_content_v2
        response = self.client.put(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify new Note was created
        event.refresh_from_db()
        self.assertTrue(event.note_links.exists())
        note_v2 = event.note_links.first().note
        self.assertNotEqual(note_v2.pk, note_v1_pk)  # Different note
        self.assertEqual(note_v2.content, notes_content_v2)
        self.assertEqual(event.notes, notes_content_v2)


class TestCaseNoteEdgeCases(APITestCase):
    """Test edge cases for Note creation and deletion."""

    def test_create_entity_with_empty_notes_no_note_created(self):
        """Empty notes should not create a Note entity."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN - Create event with empty notes dict
        data = {
            'title': 'Event Without Notes',
            'all_day': False,
            'show_end_time': True,
            'start': '2024-05-08T10:00:00Z',
            'end': '2024-05-08T14:00:00Z',
            'priority': 50,
            'notes': {},
        }
        response = self.client.post(
            reverse('planner_events_list'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from helium.planner.models import Event
        event = Event.objects.get(pk=response.data['id'])
        self.assertFalse(event.note_links.exists())
        self.assertEqual(Note.objects.filter(user=user).count(), 0)

    def test_create_entity_with_null_notes_no_note_created(self):
        """Null notes should not create a Note entity."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN - Create event with null notes
        data = {
            'title': 'Event Without Notes',
            'all_day': False,
            'show_end_time': True,
            'start': '2024-05-08T10:00:00Z',
            'end': '2024-05-08T14:00:00Z',
            'priority': 50,
            'notes': None,
        }
        response = self.client.post(
            reverse('planner_events_list'),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        from helium.planner.models import Event
        event = Event.objects.get(pk=response.data['id'])
        self.assertFalse(event.note_links.exists())
        self.assertEqual(Note.objects.filter(user=user).count(), 0)

    def test_clear_notes_deletes_linked_note(self):
        """Setting notes to empty on an entity with existing notes should delete the Note."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # First, create a note via the event
        notes_content = {'ops': [{'insert': 'Some notes\n'}]}
        data = {
            'title': event.title,
            'all_day': event.all_day,
            'show_end_time': event.show_end_time,
            'start': event.start.isoformat(),
            'end': event.end.isoformat(),
            'priority': event.priority,
            'notes': notes_content,
        }
        response = self.client.put(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertTrue(event.note_links.exists())
        note_pk = event.note_links.first().note.pk

        # WHEN - Clear the notes
        data['notes'] = {}
        response = self.client.put(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertFalse(event.note_links.exists())
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_delete_entity_deletes_linked_note(self):
        """Deleting an entity should also delete its linked Note."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(user, event)
        note_pk = note.pk

        # WHEN
        response = self.client.delete(reverse('planner_events_detail', kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())

    def test_clear_note_content_via_note_api_deletes_linked_note(self):
        """Clearing content via the Note API should delete the Note if it has linked entities."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(
            user, event, content={'ops': [{'insert': 'Some notes\n'}]}
        )
        note_pk = note.pk

        # Verify note exists and has a link
        self.assertTrue(Note.objects.filter(pk=note_pk).exists())
        self.assertTrue(NoteLink.objects.filter(note_id=note_pk).exists())

        # WHEN - Clear content via Note API (PATCH)
        data = {'content': {}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note_pk}),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - Note should be deleted and return 204
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())
        self.assertFalse(NoteLink.objects.filter(note_id=note_pk).exists())
        # Entity's notes field should also be cleared
        event.refresh_from_db()
        self.assertIsNone(event.notes)

    def test_clear_note_content_standalone_note_not_deleted(self):
        """Clearing content on a standalone Note (no linked entities) should NOT delete it."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        note = notehelper.given_note_exists(
            user, title='Standalone', content={'ops': [{'insert': 'Some content\n'}]}
        )
        note_pk = note.pk

        # Verify no links exist
        self.assertFalse(NoteLink.objects.filter(note_id=note_pk).exists())

        # WHEN - Clear content via Note API (PATCH)
        data = {'content': {}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note_pk}),
            json.dumps(data),
            content_type='application/json'
        )

        # THEN - Note should still exist with empty content
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(Note.objects.filter(pk=note_pk).exists())
        note.refresh_from_db()
        self.assertEqual(note.content, {})
