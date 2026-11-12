import copy
import json
from unittest import mock

from django.test import SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.importexport.services.legacyimportparity import upgrade_legacy_import
from helium.importexport.tests.helpers import importexporthelper
from helium.planner.models import Event, Homework, Resource, ResourceGroup, Note


def _current_file():
    return {
        'resource_groups': [{'id': 1, 'title': 'Books'}],
        'resources': [{'id': 10, 'title': 'Textbook', 'resource_group': 1}],
        'homework': [{'id': 20, 'title': 'Lab', 'resources': [10]}],
        'events': [{'id': 30, 'title': 'Talk'}],
        'reminders': [{'id': 40, 'homework': 20, 'type': enums.PUSH, 'message': 'Soon'}],
        'notes': [{'id': 5, 'title': 'Mine', 'content': {'ops': [{'insert': 'x\n'}]}, 'homework': [20]}],
    }


class TestCaseLegacyImportParity(SimpleTestCase):
    def test_current_format_file_is_left_unchanged(self):
        # GIVEN
        data = _current_file()

        # WHEN
        upgraded = upgrade_legacy_import(copy.deepcopy(data))

        # THEN
        self.assertEqual(upgraded, data)

    def test_resource_sections_and_keys_become_resources(self):
        # GIVEN
        data = {
            'material_groups': [{'id': 1}],
            'materials': [{'id': 10, 'material_group': 1}],
            'homework': [{'id': 20, 'materials': [10]}],
            'notes': [{'id': 5, 'materials': [10]}],
        }

        # WHEN
        upgraded = upgrade_legacy_import(data)

        # THEN
        self.assertEqual(upgraded['resource_groups'], [{'id': 1}])
        self.assertEqual(upgraded['resources'], [{'id': 10, 'resource_group': 1}])
        self.assertEqual(upgraded['homework'], [{'id': 20, 'resources': [10]}])
        self.assertEqual(upgraded['notes'], [{'id': 5, 'resources': [10]}])
        self.assertNotIn('materials', upgraded)
        self.assertNotIn('material_groups', upgraded)

    def test_legacy_and_current_key_together_are_rejected(self):
        for data, section in (({'materials': [], 'resources': []}, None),
                              ({'homework': [{'id': 1, 'materials': [], 'resources': []}]}, 'homework'),
                              ({'notes': [{'id': 1, 'materials': [], 'resources': []}]}, 'notes')):
            with self.subTest(section=section):
                # WHEN
                with self.assertRaises(ValidationError) as context:
                    upgrade_legacy_import(data)

                # THEN
                detail = context.exception.detail
                self.assertIn("not both", str(detail[section] if section else detail))

    def test_popup_and_text_reminders_become_push_and_the_duplicates_that_leaves_are_dropped(self):
        # GIVEN
        reminder = {'homework': 20, 'offset': 15, 'offset_type': enums.MINUTES, 'message': 'Soon',
                    'sent': False, 'dismissed': False}
        data = {'reminders': [{'id': 1, **reminder, 'type': 0}, {'id': 2, **reminder, 'type': enums.PUSH},
                              {'id': 3, **reminder, 'type': 2, 'offset': 30}]}

        # WHEN
        upgraded = upgrade_legacy_import(data)

        # THEN
        self.assertEqual([(r['id'], r['type']) for r in upgraded['reminders']], [(1, enums.PUSH), (3, enums.PUSH)])

    def test_legacy_text_becomes_an_untitled_note_linked_to_its_item(self):
        # GIVEN
        data = {
            'homework': [{'id': 20, 'comments': '<p>Due by <b>midnight</b></p>'}],
            'events': [{'id': 30, 'comments': 'Room 4'}, {'id': 31, 'comments': '   '}],
            'resources': [{'id': 10, 'details': 'ISBN 978'}],
            'notes': [{'id': '7', 'title': 'Standalone'}],
        }

        # WHEN
        upgraded = upgrade_legacy_import(data)

        # THEN
        self.assertNotIn('comments', upgraded['homework'][0])
        self.assertNotIn('details', upgraded['resources'][0])
        self.assertEqual([(n['id'], n.get('homework'), n.get('events'), n.get('resources')) for n in upgraded['notes']],
                         [('7', None, None, None), (8, [20], None, None), (9, None, [30], None), (10, None, None, [10])])
        self.assertEqual(upgraded['notes'][1]['content']['ops'][1], {'insert': 'midnight', 'attributes': {'bold': True}})
        self.assertEqual(upgraded['notes'][1]['title'], '')

    def test_legacy_text_is_dropped_when_the_file_already_links_a_note_to_the_item(self):
        # GIVEN
        data = {'homework': [{'id': 20, 'comments': 'Old text'}],
                'notes': [{'id': 5, 'content': {'ops': [{'insert': 'New\n'}]}, 'homework': ['20']}]}

        # WHEN
        upgraded = upgrade_legacy_import(data)

        # THEN
        self.assertNotIn('comments', upgraded['homework'][0])
        self.assertEqual([note['id'] for note in upgraded['notes']], [5])

    @override_settings(MAX_NOTE_SIZE=20)
    def test_legacy_text_too_large_for_a_note_is_reported_against_the_row_it_came_from(self):
        # GIVEN
        data = {'resources': [{'id': 10, 'details': 'A very long description of this resource'}]}

        # WHEN
        with self.assertRaises(ValidationError) as context:
            upgrade_legacy_import(data)

        # THEN
        message = str(context.exception.detail['resources'][0])
        self.assertTrue(message.startswith('resources id 10, details: This note is'), message)


def _older_minimal_payload():
    return {
        'course_groups': [{
            'id': 1, 'title': 'G', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
            'shown_on_calendar': True, 'overall_grade': '-1', 'user': 1,
        }],
        'courses': [{
            'id': 1, 'title': 'C', 'room': '', 'credits': '3.00', 'color': '#4986e7',
            'website': '', 'is_online': False, 'current_grade': '-1', 'teacher_name': '',
            'teacher_email': '', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
            'course_group': 1,
        }],
        'categories': [{
            'id': 1, 'title': 'Default', 'weight': '0.00', 'average_grade': '-1',
            'grade_by_weight': '0', 'color': '#4986e7', 'course': 1,
        }],
        'material_groups': [{
            'id': 1, 'title': 'MG', 'shown_on_calendar': True, 'user': 1,
        }],
        'materials': [{
            'id': 1, 'title': 'M', 'status': 0, 'condition': 0, 'website': '',
            'price': '', 'material_group': 1, 'courses': [],
        }],
        'events': [],
        'homework': [],
        'reminders': [],
        'notes': [],
        'course_schedules': [],
    }


def _imported_notes(user):
    return sorted((json.dumps(note.content, sort_keys=True), note.homework.count(), note.events.count(),
                   note.resources.count()) for note in Note.objects.for_user(user.pk))


class TestCaseLegacyImportParityViews(APITestCase):
    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_older_export_imports_the_same_as_its_current_format_equivalent(self, mock_validate_url):
        # GIVEN
        older_user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        older = importexporthelper.post_import_resource(self.client, 'legacy_export.json', content_type='text/plain')
        current_user = userhelper.given_a_user_exists_and_is_authenticated(
            self.client, username='current', email='current@test.com')

        # WHEN
        current = importexporthelper.post_import_resource(self.client, 'sample.json', content_type='text/plain')

        # THEN
        self.assertEqual(older.status_code, status.HTTP_200_OK, msg=str(older.data))
        self.assertEqual(current.status_code, status.HTTP_200_OK, msg=str(current.data))
        self.assertEqual({key: value for key, value in older.data.items() if key != 'ids'},
                         {key: value for key, value in current.data.items() if key != 'ids'})
        self.assertEqual(_imported_notes(older_user), _imported_notes(current_user))
        self.assertEqual(
            sorted(Homework.objects.for_user(older_user.pk).values_list('title', 'resources__title'), key=str),
            sorted(Homework.objects.for_user(current_user.pk).values_list('title', 'resources__title'), key=str))

    def test_import_turns_comments_and_details_into_linked_quill_notes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        import_data = {
            'course_groups': [{
                'id': 1,
                'title': 'Test Group',
                'start_date': '2024-01-01',
                'end_date': '2024-05-01',
                'shown_on_calendar': True,
                'overall_grade': '-1',
                'user': 1
            }],
            'courses': [{
                'id': 1,
                'title': 'Test Course',
                'room': '',
                'credits': '3.00',
                'color': '#4986e7',
                'website': '',
                'is_online': False,
                'current_grade': '-1',
                'teacher_name': '',
                'teacher_email': '',
                'start_date': '2024-01-01',
                'end_date': '2024-05-01',
                'course_group': 1
            }],
            'categories': [{
                'id': 1,
                'title': 'Uncategorized',
                'weight': '0.00',
                'average_grade': '-1',
                'grade_by_weight': '0',
                'color': '#4986e7',
                'course': 1
            }],
            'material_groups': [{
                'id': 1,
                'title': 'Test Materials',
                'shown_on_calendar': True,
                'user': 1
            }],
            'materials': [{
                'id': 1,
                'title': 'Test Book',
                'status': 0,
                'condition': 0,
                'website': '',
                'price': '',
                'details': '<b>ISBN:</b> 978-1234567890',
                'material_group': 1,
                'courses': []
            }],
            'events': [{
                'id': 1,
                'title': 'Test Event',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-01T10:00:00Z',
                'end': '2024-02-01T11:00:00Z',
                'priority': 50,
                'url': None,
                'comments': '<ul><li>Item 1</li><li>Item 2</li></ul>',
                'user': 1
            }],
            'homework': [{
                'id': 1,
                'title': 'Test Assignment',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-01T10:00:00Z',
                'end': '2024-02-01T12:00:00Z',
                'priority': 50,
                'url': None,
                'comments': '<p>Due by <strong>midnight</strong></p>',
                'current_grade': '-1/100',
                'completed': False,
                'category': 1,
                'materials': [],
                'course': 1
            }],
            'reminders': [],
            'course_schedules': []
        }

        # WHEN
        response = importexporthelper.post_import(self.client, import_data, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        resource = Resource.objects.first()
        self.assertTrue(resource.notes_set.exists())
        resource_note = resource.notes_set.first()
        self.assertIn('ops', resource_note.content)
        bold_op = next((op for op in resource_note.content['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'ISBN:')

        event = Event.objects.first()
        self.assertTrue(event.notes_set.exists())
        event_note = event.notes_set.first()
        self.assertIn('ops', event_note.content)
        list_op = next((op for op in event_note.content['ops'] if op.get('attributes', {}).get('list')), None)
        self.assertIsNotNone(list_op)
        self.assertEqual(list_op['attributes']['list'], 'bullet')

        homework = Homework.objects.first()
        self.assertTrue(homework.notes_set.exists())
        homework_note = homework.notes_set.first()
        self.assertIn('ops', homework_note.content)
        bold_op = next((op for op in homework_note.content['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'midnight')

        self.assertEqual(Note.objects.filter(user=user).count(), 3)

    def test_import_accepts_top_level_resources(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Resource.objects.count(), 1)

    def test_import_rejects_both_top_level_resources_and_resources(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()
        payload['resources'] = list(payload['materials'])

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Provide either 'resources' or 'materials'", str(response.data))
        self.assertEqual(Resource.objects.count(), 0)

    def test_import_maps_homework_resources_like_resources(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()
        homework_row = {
            'all_day': False, 'show_end_time': False, 'start': '2024-02-01T10:00:00Z',
            'end': '2024-02-01T12:00:00Z', 'priority': 50, 'current_grade': '-1/100', 'completed': False,
            'category': 1, 'course': 1,
        }
        payload['homework'] = [
            {'id': 20, 'title': 'Current', 'resources': [1], **homework_row},
            {'id': 21, 'title': 'Older', 'materials': [1], **homework_row},
        ]

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=str(response.data))
        resource = Resource.objects.get()
        for title in ('Current', 'Older'):
            self.assertEqual(list(Homework.objects.get(title=title).resources.all()), [resource], msg=title)

    def test_import_maps_resource_resource_group_like_resource_group(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()
        resource_row = {'status': 0, 'condition': 0, 'website': '', 'price': '', 'courses': []}
        payload['materials'] = [
            {'id': 1, 'title': 'Current', 'resource_group': 1, **resource_row},
            {'id': 2, 'title': 'Older', 'material_group': 1, **resource_row},
        ]

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=str(response.data))
        resource_group = ResourceGroup.objects.get()
        for title in ('Current', 'Older'):
            self.assertEqual(Resource.objects.get(title=title).resource_group, resource_group, msg=title)

    def test_import_rejects_note_with_both_resources_and_resources(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()
        payload['notes'] = [{
            'id': 1, 'title': 'Bad', 'content': {'ops': [{'insert': 'x\n'}]},
            'resources': [1], 'materials': [1],
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Provide either 'resources' or 'materials'", str(response.data))
        self.assertEqual(Note.objects.count(), 0)

    def test_import_maps_note_resources_like_resources(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = _older_minimal_payload()
        payload['notes'] = [{
            'id': 1, 'title': 'Alias', 'content': {'ops': [{'insert': 'x\n'}]},
            'materials': [1],
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload, content_type='text/plain')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note = Note.objects.get(title='Alias')
        self.assertEqual(note.resources.count(), 1)
