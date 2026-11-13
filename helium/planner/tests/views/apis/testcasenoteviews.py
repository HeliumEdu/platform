import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.helpers import commonhelper
from helium.planner.models import Note
from helium.planner.tests.helpers import (
    notehelper, eventhelper, homeworkhelper, coursegrouphelper, coursehelper,
    resourcegrouphelper, resourcehelper
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
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

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

    def test_link_to_another_users_homework_returns_404(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user2)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Note', 'homework': [homework.pk]}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Note.objects.count(), 0)

    def test_link_to_malformed_homework_id_returns_400(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Note', 'homework': ['abc']}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Note.objects.count(), 0)

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

    def test_content_search_query_matches_plain_text(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        match = notehelper.given_note_exists(
            user, title='Bio', content={'ops': [{'insert': 'Mitochondria are the ', 'attributes': {'bold': True}},
                                                {'insert': 'powerhouse\n'}]})
        notehelper.given_note_exists(user, title='Chem', content={'ops': [{'insert': 'Moles and molarity\n'}]})

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=POWERHOUSE')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [match.pk])
        self.assertNotIn('content', response.data[0])

    def test_content_search_query_ignores_delta_syntax(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        notehelper.given_note_exists(
            user, title='Formatted', content={'ops': [{'insert': 'text', 'attributes': {'bold': True, 'list': 'bullet'}},
                                                     {'insert': '\n'}]})

        # WHEN
        responses = {delta_token: self.client.get(reverse('planner_notes_list') + f'?search={delta_token}')
                     for delta_token in ('insert', 'attributes', 'bold', 'list', 'bullet', 'ops')}

        # THEN
        for delta_token, response in responses.items():
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 0, msg=f'`{delta_token}` should not match Delta syntax')

    def test_search_query_applies_requested_ordering(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        beta = notehelper.given_note_exists(user, title='Beta Krebs')
        alpha = notehelper.given_note_exists(user, title='Alpha Krebs')
        notehelper.given_note_exists(user, title='Gamma Other')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=krebs&ordering=title')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [alpha.pk, beta.pk])

    def test_search_query_requires_every_term(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        match = notehelper.given_note_exists(user, title='Week 3',
                                             content={'ops': [{'insert': 'Krebs cycle overview\n'}]})
        notehelper.given_note_exists(user, title='Week 4', content={'ops': [{'insert': 'Krebs quiz prep\n'}]})

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=krebs overview')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [match.pk])

    def test_search_query_folds_diacritics_and_edge_punctuation(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        match = notehelper.given_note_exists(user, title='Café Notes', content={'ops': [{'insert': 'Über\n'}]})
        notehelper.given_note_exists(user, title='Other')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=cafe uber.')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [match.pk])

    def test_search_query_quoted_phrase_must_match_contiguously(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        match = notehelper.given_note_exists(user, title='Lab Report Draft')
        notehelper.given_note_exists(user, title='Report on the lab')

        # WHEN
        phrase = self.client.get(reverse('planner_notes_list') + '?search="lab report"')
        words = self.client.get(reverse('planner_notes_list') + '?search=lab report')

        # THEN
        self.assertEqual([note['id'] for note in phrase.data], [match.pk])
        self.assertEqual(len(words.data), 2)

    def test_search_query_matches_linked_entity_title(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course, title='Lab Report Draft')
        linked = notehelper.given_note_linked_to_homework(user, homework)
        notehelper.given_note_exists(user, title='Unrelated')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=lab report')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [linked.pk])

    def test_search_query_with_include_content_still_matches(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        match = notehelper.given_note_exists(user, content={'ops': [{'insert': 'osmosis\n'}]})

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?search=osmosis&include_content=true')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([note['id'] for note in response.data], [match.pk])
        self.assertEqual(response.data[0]['content'], match.content)

    def test_filter_by_linked_entity_type(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note_with_event = notehelper.given_note_linked_to_event(user, event)
        notehelper.given_note_exists(user, title='Standalone')
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=event')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], note_with_event.pk)

    def test_filter_by_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        other_course = coursehelper.given_course_exists(course_group, title='Other Course')
        homework_note = notehelper.given_note_linked_to_homework(user, homeworkhelper.given_homework_exists(course))
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource_note = notehelper.given_note_linked_to_resource(
            user, resourcehelper.given_resource_exists(resource_group, courses=[course]))
        notehelper.given_note_linked_to_homework(user, homeworkhelper.given_homework_exists(other_course))
        notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + f'?course={course.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({homework_note.pk, resource_note.pk}, {note['id'] for note in response.data})

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
        self.assertEqual(response.data['course_id'], course.pk)

    def test_get_note_includes_homework_due_and_completed(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course, completed=True)
        note = notehelper.given_note_linked_to_homework(user, homework)
        # WHEN
        response = self.client.get(reverse('planner_notes_detail', kwargs={'pk': note.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['linked_entity_due'], homework.start)
        self.assertEqual(response.data['linked_entity_completed'], True)
        # WHEN
        response = self.client.get(reverse('planner_notes_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['linked_entity_due'], homework.start)
        self.assertEqual(response.data[0]['linked_entity_completed'], True)

    def test_get_note_homework_fields_null_for_non_homework_link(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        notehelper.given_note_linked_to_event(user, event)
        response = self.client.get(reverse('planner_notes_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data[0]['linked_entity_due'])
        self.assertIsNone(response.data[0]['linked_entity_completed'])

    def test_get_note_includes_link_info_with_resource(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)
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

    def test_clear_note_content_keeps_linked_note_with_title(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(
            user, event, title='Lab prep', content={'ops': [{'insert': 'Some notes\n'}]}
        )
        data = {'content': {'ops': [{'insert': '\n'}]}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.title, 'Lab prep')
        self.assertEqual(note.content, {'ops': [{'insert': '\n'}]})

    def test_clear_note_title_and_content_deletes_linked_note(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        note = notehelper.given_note_linked_to_event(
            user, event, title='Lab prep', content={'ops': [{'insert': 'Some notes\n'}]}
        )
        data = {'title': ' ', 'content': {'ops': [{'insert': '\n'}]}}
        response = self.client.patch(
            reverse('planner_notes_detail', kwargs={'pk': note.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())

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
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource1 = resourcehelper.given_resource_exists(resource_group)
        resource2 = resourcehelper.given_resource_exists(resource_group)
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
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)
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

    def test_filter_shown_on_calendar_true_includes_visible_and_unlinked(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        visible_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=True)
        hidden_group = coursegrouphelper.given_course_group_exists(user, title='Hidden', shown_on_calendar=False)
        visible_course = coursehelper.given_course_exists(visible_group)
        hidden_course = coursehelper.given_course_exists(hidden_group, title='Hidden Course')
        hw_visible = homeworkhelper.given_homework_exists(visible_course)
        hw_hidden = homeworkhelper.given_homework_exists(hidden_course, title='Hidden HW')

        note_visible_hw = notehelper.given_note_linked_to_homework(user, hw_visible, title='Visible HW Note')
        note_hidden_hw = notehelper.given_note_linked_to_homework(user, hw_hidden, title='Hidden HW Note')

        event = eventhelper.given_event_exists(user)
        note_event = notehelper.given_note_linked_to_event(user, event, title='Event Note')

        note_standalone = notehelper.given_note_exists(user, title='Standalone Note')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?shown_on_calendar=true')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {n['id'] for n in response.data}
        self.assertIn(note_visible_hw.pk, returned_ids)
        self.assertNotIn(note_hidden_hw.pk, returned_ids)
        self.assertIn(note_event.pk, returned_ids)
        self.assertIn(note_standalone.pk, returned_ids)

    def test_filter_shown_on_calendar_false_returns_hidden_group_and_unlinked_notes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        visible_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=True)
        hidden_group = coursegrouphelper.given_course_group_exists(user, title='Hidden', shown_on_calendar=False)
        visible_course = coursehelper.given_course_exists(visible_group)
        hidden_course = coursehelper.given_course_exists(hidden_group, title='Hidden Course')
        hw_visible = homeworkhelper.given_homework_exists(visible_course)
        hw_hidden = homeworkhelper.given_homework_exists(hidden_course, title='Hidden HW')

        note_visible_hw = notehelper.given_note_linked_to_homework(user, hw_visible, title='Visible HW Note')
        note_hidden_hw = notehelper.given_note_linked_to_homework(user, hw_hidden, title='Hidden HW Note')

        event = eventhelper.given_event_exists(user)
        note_event = notehelper.given_note_linked_to_event(user, event, title='Event Note')
        note_standalone = notehelper.given_note_exists(user, title='Standalone Note')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?shown_on_calendar=false')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {n['id'] for n in response.data}
        self.assertNotIn(note_visible_hw.pk, returned_ids)
        self.assertIn(note_hidden_hw.pk, returned_ids)
        self.assertIn(note_event.pk, returned_ids)
        self.assertIn(note_standalone.pk, returned_ids)

    def test_filter_shown_on_calendar_with_resource_link(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        visible_resource_group = resourcegrouphelper.given_resource_group_exists(user, shown_on_calendar=True)
        hidden_resource_group = resourcegrouphelper.given_resource_group_exists(
            user, title='Hidden Resources', shown_on_calendar=False
        )
        visible_resource = resourcehelper.given_resource_exists(visible_resource_group)
        hidden_resource = resourcehelper.given_resource_exists(hidden_resource_group, title='Hidden Material')

        note_visible = notehelper.given_note_linked_to_resource(user, visible_resource, title='Visible Res Note')
        note_hidden = notehelper.given_note_linked_to_resource(user, hidden_resource, title='Hidden Res Note')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?shown_on_calendar=true')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {n['id'] for n in response.data}
        self.assertIn(note_visible.pk, returned_ids)
        self.assertNotIn(note_hidden.pk, returned_ids)

    def test_filter_shown_on_calendar_without_param_returns_all(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        hidden_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=False)
        hidden_course = coursehelper.given_course_exists(hidden_group, title='Hidden Course')
        hw_hidden = homeworkhelper.given_homework_exists(hidden_course, title='Hidden HW')

        note_hidden = notehelper.given_note_linked_to_homework(user, hw_hidden, title='Hidden Note')
        note_standalone = notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        response = self.client.get(reverse('planner_notes_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {n['id'] for n in response.data}
        self.assertIn(note_hidden.pk, returned_ids)
        self.assertIn(note_standalone.pk, returned_ids)

    def test_create_note_linked_to_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Class Note', 'courses': [course.pk]}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['courses'], [course.pk])
        self.assertEqual(response.data['linked_entity_type'], 'course')
        self.assertEqual(response.data['linked_entity_title'], course.title)
        self.assertEqual(response.data['course_id'], course.pk)
        self.assertEqual(response.data['course_color'], course.color)
        self.assertEqual(list(Note.objects.get(pk=response.data['id']).courses.all()), [course])

    def test_link_to_another_users_course_returns_404(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user2)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Note', 'courses': [course.pk]}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Note.objects.count(), 0)

    def test_note_rejects_course_with_another_link_type(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Note', 'courses': [course.pk], 'homework': [homework.pk]}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one type', str(response.data))
        self.assertEqual(Note.objects.count(), 0)

    def test_note_rejects_multiple_courses(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group, title='Other Course')

        # WHEN
        response = self.client.post(reverse('planner_notes_list'),
                                    json.dumps({'title': 'Note', 'courses': [course1.pk, course2.pk]}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('only be linked to one class', str(response.data))

    def test_note_rejects_linking_to_course_with_existing_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        notehelper.given_note_linked_to_course(user, course)
        new_note = notehelper.given_note_exists(user)

        # WHEN
        response = self.client.put(reverse('planner_notes_detail', kwargs={'pk': new_note.pk}),
                                   json.dumps({'title': new_note.title, 'content': new_note.content,
                                               'courses': [course.pk]}),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('This class already has a linked note', str(response.data))

    def test_filter_by_linked_entity_type_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_note = notehelper.given_note_linked_to_course(user, course)
        notehelper.given_note_linked_to_homework(user, homeworkhelper.given_homework_exists(course))
        notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=course')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([course_note.pk], [note['id'] for note in response.data])

    def test_filter_by_course_includes_its_own_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        other_course = coursehelper.given_course_exists(course_group, title='Other Course')
        course_note = notehelper.given_note_linked_to_course(user, course)
        homework_note = notehelper.given_note_linked_to_homework(user, homeworkhelper.given_homework_exists(course))
        notehelper.given_note_linked_to_course(user, other_course)

        # WHEN
        response = self.client.get(reverse('planner_notes_list') + f'?course={course.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({course_note.pk, homework_note.pk}, {note['id'] for note in response.data})

    def test_course_linked_note_is_not_standalone(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course_note = notehelper.given_note_linked_to_course(user, coursehelper.given_course_exists(course_group))
        standalone = notehelper.given_note_exists(user, title='Standalone')

        # WHEN
        standalone_response = self.client.get(reverse('planner_notes_list') + '?linked_entity_type=standalone')
        unlinked_response = self.client.get(reverse('planner_notes_list') + '?has_link=false')
        linked_response = self.client.get(reverse('planner_notes_list') + '?has_link=true')

        # THEN
        self.assertEqual([standalone.pk], [note['id'] for note in standalone_response.data])
        self.assertEqual([standalone.pk], [note['id'] for note in unlinked_response.data])
        self.assertEqual([course_note.pk], [note['id'] for note in linked_response.data])

    def test_filter_shown_on_calendar_with_course_link(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        visible_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=True)
        hidden_group = coursegrouphelper.given_course_group_exists(user, title='Hidden Group', shown_on_calendar=False)
        note_visible = notehelper.given_note_linked_to_course(user, coursehelper.given_course_exists(visible_group))
        note_hidden = notehelper.given_note_linked_to_course(
            user, coursehelper.given_course_exists(hidden_group, title='Hidden Course'))

        # WHEN
        shown_response = self.client.get(reverse('planner_notes_list') + '?shown_on_calendar=true')
        hidden_response = self.client.get(reverse('planner_notes_list') + '?shown_on_calendar=false')

        # THEN
        self.assertEqual([note_visible.pk], [note['id'] for note in shown_response.data])
        self.assertEqual([note_hidden.pk], [note['id'] for note in hidden_response.data])

    def test_delete_course_deletes_linked_note(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        note = notehelper.given_note_linked_to_course(user, course)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_detail',
                                              kwargs={'course_group': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Note.objects.filter(pk=note.pk).exists())
