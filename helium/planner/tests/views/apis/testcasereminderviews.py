__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.7"

import datetime
import json
from datetime import timedelta
from urllib.parse import quote

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, eventhelper, reminderhelper


class TestCaseReminderViews(APITestCase):
    def test_reminder_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_reminders_list')),
            self.client.post(reverse('planner_reminders_list')),
            self.client.get(reverse('planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_reminders_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_reminders(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user2)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        homework1 = homeworkhelper.given_homework_exists(course1)
        homework2 = homeworkhelper.given_homework_exists(course2)
        homework3 = homeworkhelper.given_homework_exists(course3)
        homework4 = homeworkhelper.given_homework_exists(course3)
        reminderhelper.given_reminder_exists(user1, homework=homework1)
        reminderhelper.given_reminder_exists(user2, homework=homework2)
        reminderhelper.given_reminder_exists(user2, homework=homework3)
        reminderhelper.given_reminder_exists(user2, homework=homework4)
        reminderhelper.given_reminder_exists(user2, homework=homework4)
        reminderhelper.given_reminder_exists(user1, event=event1)
        reminderhelper.given_reminder_exists(user2, event=event2)
        reminderhelper.given_reminder_exists(user2, event=event2)

        # WHEN
        response1 = self.client.get(reverse('planner_reminders_list'))
        response2 = self.client.get(reverse('planner_reminders_list') + f'?homework={homework4.pk}')
        response3 = self.client.get(reverse('planner_reminders_list') + f'?event={event2.pk}')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        self.assertEqual(Reminder.objects.count(), 8)
        self.assertEqual(len(response1.data), 6)
        self.assertEqual(len(response2.data), 2)
        self.assertEqual(len(response3.data), 2)

    def test_create_event_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP,
            'event': event.pk,
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'start_of_range': (event.start - timedelta(hours=1)).isoformat(),
            'sent': False,
            'user': user.pk
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reminder.objects.count(), 1)
        course = Reminder.objects.get(pk=response.data['id'])
        reminderhelper.verify_reminder_matches_data(self, course, data)
        reminderhelper.verify_reminder_matches_data(self, course, response.data)

    def test_create_homework_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP,
            'homework': homework.pk,
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'start_of_range': (homework.start - timedelta(hours=1)).isoformat(),
            'sent': False,
            'user': user.pk
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reminder.objects.count(), 1)
        reminder = Reminder.objects.get(pk=response.data['id'])
        reminderhelper.verify_reminder_matches_data(self, reminder, data)
        reminderhelper.verify_reminder_matches_data(self, reminder, response.data)

    def test_create_orphaned_reminder_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'start_of_range': '2014-05-08T12:00:00Z',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP,
        }
        response = self.client.post(
            reverse('planner_reminders_list'),
            data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('One of', response.data['non_field_errors'][0])

    def test_create_reminder_multiple_parents_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'start_of_range': '2014-05-08T12:00:00Z',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP,
            'homework': homework.pk,
            'event': event.pk,
        }
        response = self.client.post(
            reverse('planner_reminders_list'),
            data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Only one of', response.data['non_field_errors'][0])

    def test_get_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        response = self.client.get(reverse('planner_reminders_detail',
                                           kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminderhelper.verify_reminder_matches_data(self, reminder, response.data)

    def test_update_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        self.assertEqual(reminder.title, '🌴 Test Reminder')

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP
        }
        response = self.client.put(reverse('planner_reminders_detail',
                                           kwargs={'pk': reminder.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        reminder = Reminder.objects.get(pk=reminder.pk)
        reminderhelper.verify_reminder_matches_data(self, reminder, response.data)

    def test_update_reminder_parent_updates(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'homework': homework.pk
        }
        response = self.client.patch(reverse('planner_reminders_detail',
                                             kwargs={'pk': reminder.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['homework'], homework.pk)
        self.assertIsNone(response.data['event'])

    def test_delete_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        response = self.client.delete(reverse('planner_reminders_detail',
                                              kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reminder.objects.filter(pk=reminder.pk).exists())
        self.assertEqual(Reminder.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user2)
        reminder = reminderhelper.given_reminder_exists(user1, event=event1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course2 = coursehelper.given_course_exists(course_group2)
        homework2 = homeworkhelper.given_homework_exists(course2)

        # WHEN
        responses = [
            self.client.post(reverse('planner_reminders_list'),
                             json.dumps({'event': event2.pk}),
                             content_type='application/json'),
            self.client.post(reverse('planner_reminders_list'),
                             json.dumps({'homework': homework2.pk}),
                             content_type='application/json'),
            self.client.put(
                reverse('planner_reminders_detail',
                        kwargs={'pk': reminder.pk}),
                json.dumps({'event': event2.pk}),
                content_type='application/json'),
            self.client.put(
                reverse('planner_reminders_detail',
                        kwargs={'pk': reminder.pk}),
                json.dumps({'homework': homework2.pk}),
                content_type='application/json')
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)
        event_reminder = reminderhelper.given_reminder_exists(user1, event=event)
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminderhelper.given_reminder_exists(user1, homework=homework)

        # WHEN
        responses = [
            self.client.get(reverse('planner_reminders_list') + f'?event={event.pk}'),
            self.client.get(reverse('planner_reminders_list') + f'?homework={homework.pk}'),
            self.client.get(reverse('planner_reminders_detail', kwargs={'pk': event_reminder.pk})),
            self.client.put(reverse('planner_reminders_detail', kwargs={'pk': event_reminder.pk})),
            self.client.delete(reverse('planner_reminders_detail', kwargs={'pk': event_reminder.pk}))
        ]

        # THEN
        self.assertTrue(Reminder.objects.filter(pk=event_reminder.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        start_of_range = reminder.start_of_range

        # WHEN
        data = {
            'start_of_range': '2014-05-08T12:00:00Z'
        }
        response = self.client.put(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder = Reminder.objects.get(pk=reminder.id)
        self.assertEqual(reminder.start_of_range, start_of_range)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'offset': 'asdf'
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('offset', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'offset': 'asdf'
        }
        response = self.client.put(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('offset', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_reminders_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('matches the given query', response.data['detail'].lower())

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework1 = homeworkhelper.given_homework_exists(course,
                                                         start=datetime.datetime(2017, 5, 8, 16, 0, 0,
                                                                                 tzinfo=timezone.utc),
                                                         end=datetime.datetime(2017, 5, 8, 17, 0, 0,
                                                                               tzinfo=timezone.utc))
        homework2 = homeworkhelper.given_homework_exists(course,
                                                         start=timezone.now() + timedelta(days=1),
                                                         end=timezone.now() + timedelta(days=1, minutes=30))
        reminderhelper.given_reminder_exists(user, homework=homework1)
        reminderhelper.given_reminder_exists(user, homework=homework2)

        response = self.client.get(
            reverse('planner_reminders_list') + f'?start_of_range__lte={quote(timezone.now().isoformat())}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
