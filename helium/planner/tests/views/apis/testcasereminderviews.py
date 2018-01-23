import json
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, eventhelper, reminderhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseReminderViews(TestCase):
    def test_reminder_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_reminders_list')),
            self.client.post(reverse('api_planner_reminders_list')),
            self.client.get(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_reminders(self):
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
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
        response1 = self.client.get(reverse('api_planner_reminders_list'))
        response2 = self.client.get(reverse('api_planner_reminders_list') + '?homework={}'.format(homework4.pk))
        response3 = self.client.get(reverse('api_planner_reminders_list') + '?event={}'.format(event2.pk))

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
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
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
            'from_admin': False,
            'user': user.pk
        }
        response = self.client.post(reverse('api_planner_reminders_list'),
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
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
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
            'from_admin': False,
            'user': user.pk
        }
        response = self.client.post(reverse('api_planner_reminders_list'),
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
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

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
            reverse('api_planner_reminders_list'),
            data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('one of', response.data['non_field_errors'][0])

    def test_get_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        response = self.client.get(reverse('api_planner_reminders_detail',
                                           kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminderhelper.verify_reminder_matches_data(self, reminder, response.data)

    def test_update_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'title': 'some title',
            'message': 'some message',
            'offset': 1,
            'offset_type': enums.HOURS,
            'type': enums.POPUP,
            # Intentionally NOT changing these value
            'event': event.pk
        }
        response = self.client.put(reverse('api_planner_reminders_detail',
                                           kwargs={'pk': reminder.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        reminder = Reminder.objects.get(pk=reminder.pk)
        reminderhelper.verify_reminder_matches_data(self, reminder, response.data)

    def test_delete_reminder_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        response = self.client.delete(reverse('api_planner_reminders_detail',
                                              kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reminder.objects.filter(pk=reminder.pk).exists())
        self.assertEqual(Reminder.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user1')
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user2)
        reminder = reminderhelper.given_reminder_exists(user1, event=event1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course2 = coursehelper.given_course_exists(course_group2)
        homework2 = homeworkhelper.given_homework_exists(course2)

        # WHEN
        responses = [
            self.client.post(reverse('api_planner_reminders_list'),
                             json.dumps({'event': event2.pk}),
                             content_type='application/json'),
            self.client.post(reverse('api_planner_reminders_list'),
                             json.dumps({'homework': homework2.pk}),
                             content_type='application/json'),
            self.client.put(
                reverse('api_planner_reminders_detail',
                        kwargs={'pk': reminder.pk}),
                json.dumps({'event': event2.pk}),
                content_type='application/json'),
            self.client.put(
                reverse('api_planner_reminders_detail',
                        kwargs={'pk': reminder.pk}),
                json.dumps({'homework': homework2.pk}),
                content_type='application/json')
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)
        event_reminder = reminderhelper.given_reminder_exists(user1, event=event)
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminderhelper.given_reminder_exists(user1, homework=homework)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_reminders_list') + '?event={}'.format(event.pk)),
            self.client.get(reverse('api_planner_reminders_list') + '?homework={}'.format(homework.pk)),
            self.client.get(reverse('api_planner_reminders_detail', kwargs={'pk': event_reminder.pk})),
            self.client.put(reverse('api_planner_reminders_detail', kwargs={'pk': event_reminder.pk})),
            self.client.delete(reverse('api_planner_reminders_detail', kwargs={'pk': event_reminder.pk}))
        ]

        # THEN
        self.assertTrue(Reminder.objects.filter(pk=event_reminder.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        sent = reminder.sent
        from_admin = reminder.from_admin

        # WHEN
        data = {
            'from_admin': True,
            # Intentionally NOT changing these value
            'title': reminder.title,
            'message': reminder.message,
            'start_of_range': reminder.start_of_range.isoformat(),
            'event': reminder.event.pk
        }
        response = self.client.put(reverse('api_planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder = Reminder.objects.get(pk=reminder.id)
        self.assertEqual(reminder.from_admin, from_admin)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'offset': 'asdf'
        }
        response = self.client.post(reverse('api_planner_reminders_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('offset', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        data = {
            'offset': 'asdf'
        }
        response = self.client.put(reverse('api_planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('offset', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_reminders_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())
