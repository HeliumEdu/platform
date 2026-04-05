__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
from datetime import timedelta
from urllib.parse import quote

import pytz
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, eventhelper, reminderhelper, categoryhelper, courseschedulehelper


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
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
            'dismissed': False,
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
            'dismissed': False,
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
        reminder.refresh_from_db()
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

    def test_update_event_reminder_offset_recalculates_start_of_range_and_resets_sent(self):
        # GIVEN a sent reminder whose event is in the near future; the current offset places
        # start_of_range outside the send window, so changing to a smaller offset should move
        # start_of_range into the future (>= window_start) and reset sent=False.
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user, start=timezone.now() + timedelta(minutes=30),
                                               end=timezone.now() + timedelta(minutes=90))
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=60,
                                                        offset_type=enums.MINUTES, sent=True)

        # WHEN the offset is reduced so start_of_range moves into the future
        data = {'offset': 5, 'offset_type': enums.MINUTES}
        response = self.client.patch(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                     json.dumps(data), content_type='application/json')

        # THEN start_of_range is recalculated to the exact expected value and sent is reset
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder.refresh_from_db()
        event.refresh_from_db()
        self.assertEqual(reminder.start_of_range, event.start - timedelta(minutes=5))
        self.assertFalse(reminder.sent)

    def test_update_event_reminder_offset_recalculates_start_of_range_without_resetting_sent(self):
        # GIVEN a sent reminder on a far-past event; any offset still leaves start_of_range
        # well outside the send window, so sent should remain True.
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)  # default start=2017-05-08 12:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=15,
                                                        offset_type=enums.MINUTES, sent=True)

        # WHEN the offset is changed (start_of_range stays deep in the past)
        data = {'offset': 30, 'offset_type': enums.MINUTES}
        response = self.client.patch(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                     json.dumps(data), content_type='application/json')

        # THEN start_of_range reflects the new offset exactly and sent is unchanged
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range,
                         datetime.datetime(2017, 5, 8, 11, 30, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)

    def test_update_homework_reminder_offset_recalculates_start_of_range_and_resets_sent(self):
        # GIVEN a sent reminder whose homework is in the near future; reducing the offset moves
        # start_of_range into the future, which should reset sent=False.
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + timedelta(minutes=30),
                                                        end=timezone.now() + timedelta(minutes=90))
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=60,
                                                        offset_type=enums.MINUTES, sent=True)

        # WHEN the offset is reduced so start_of_range moves into the future
        data = {'offset': 5, 'offset_type': enums.MINUTES}
        response = self.client.patch(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                     json.dumps(data), content_type='application/json')

        # THEN start_of_range is recalculated to the exact expected value and sent is reset
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder.refresh_from_db()
        homework.refresh_from_db()
        self.assertEqual(reminder.start_of_range, homework.start - timedelta(minutes=5))
        self.assertFalse(reminder.sent)

    def test_update_homework_reminder_offset_recalculates_start_of_range_without_resetting_sent(self):
        # GIVEN a sent reminder on far-past homework; changing the offset leaves start_of_range
        # well outside the send window, so sent should remain True.
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)  # default start=2017-05-08 16:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, offset=15,
                                                        offset_type=enums.MINUTES, sent=True)

        # WHEN the offset is changed (start_of_range stays deep in the past)
        data = {'offset': 30, 'offset_type': enums.MINUTES}
        response = self.client.patch(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                                     json.dumps(data), content_type='application/json')

        # THEN start_of_range reflects the new offset exactly and sent is unchanged
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range,
                         datetime.datetime(2017, 5, 8, 15, 30, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)

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

    def test_delete_repeating_course_reminder_cleans_up_series(self):
        # GIVEN a repeating course reminder series with one unsent (active) and one sent (past) reminder
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        unsent = reminderhelper.given_reminder_exists(user, course=course, repeating=True, sent=False,
                                                      type=enums.PUSH)
        sent = reminderhelper.given_reminder_exists(user, course=course, repeating=True, sent=True,
                                                    type=enums.PUSH)
        # A reminder in a different series (different course) that must not be deleted
        other_course_reminder = reminderhelper.given_reminder_exists(user, course=course2, repeating=True,
                                                                     sent=False, type=enums.PUSH)
        # A reminder in a different series (different type) that must not be deleted
        other_type_reminder = reminderhelper.given_reminder_exists(user, course=course, repeating=True,
                                                                   sent=False, type=enums.EMAIL)

        # WHEN the unsent reminder is deleted
        response = self.client.delete(reverse('planner_reminders_detail', kwargs={'pk': unsent.pk}),
                                      HTTP_X_CLIENT_VERSION='3.5.0')

        # THEN the unsent and its sent series counterpart are both deleted; unrelated reminders are untouched
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reminder.objects.filter(pk=unsent.pk).exists())
        self.assertFalse(Reminder.objects.filter(pk=sent.pk).exists())
        self.assertTrue(Reminder.objects.filter(pk=other_course_reminder.pk).exists())
        self.assertTrue(Reminder.objects.filter(pk=other_type_reminder.pk).exists())

    def test_delete_repeating_course_reminder_only_deletes_matching_offset_series(self):
        # GIVEN two PUSH course reminder series on the same course differing only by offset:
        # a 30-min series (unsent + sent history) and a 10-min series (unsent only)
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        unsent_30 = reminderhelper.given_reminder_exists(user, course=course, repeating=True, sent=False,
                                                         type=enums.PUSH, offset=30)
        sent_30 = reminderhelper.given_reminder_exists(user, course=course, repeating=True, sent=True,
                                                       type=enums.PUSH, offset=30)
        unsent_10 = reminderhelper.given_reminder_exists(user, course=course, repeating=True, sent=False,
                                                         type=enums.PUSH, offset=10)

        # WHEN the 30-min reminder is deleted
        response = self.client.delete(reverse('planner_reminders_detail', kwargs={'pk': unsent_30.pk}),
                                      HTTP_X_CLIENT_VERSION='3.5.0')

        # THEN only the 30-min series (unsent + sent) is deleted; the 10-min series is untouched
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reminder.objects.filter(pk=unsent_30.pk).exists())
        self.assertFalse(Reminder.objects.filter(pk=sent_30.pk).exists())
        self.assertTrue(Reminder.objects.filter(pk=unsent_10.pk).exists())

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

    def test_no_access_object_owned_by_another_user(self):
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
        reminder.refresh_from_db()
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

    def test_get_reminders_returns_nested_homework_with_course(self):
        """Verify that GET /reminders/ returns nested homework and course objects, not just IDs."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework)

        # WHEN
        response = self.client.get(reverse('planner_reminders_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        reminder_data = response.data[0]
        # Verify homework is a nested object, not just an ID
        self.assertIsInstance(reminder_data['homework'], dict)
        self.assertEqual(reminder_data['homework']['id'], homework.pk)
        self.assertEqual(reminder_data['homework']['title'], homework.title)

        # Verify course is nested within homework as an object, not just an ID
        self.assertIsInstance(reminder_data['homework']['course'], dict)
        self.assertEqual(reminder_data['homework']['course']['id'], course.pk)
        self.assertEqual(reminder_data['homework']['course']['title'], course.title)

    def test_get_reminder_by_id_returns_nested_homework_with_course(self):
        """Verify that GET /reminders/{id}/ returns nested homework and course objects."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework)

        # WHEN
        response = self.client.get(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify homework is a nested object, not just an ID
        self.assertIsInstance(response.data['homework'], dict)
        self.assertEqual(response.data['homework']['id'], homework.pk)

        # Verify course is nested within homework as an object, not just an ID
        self.assertIsInstance(response.data['homework']['course'], dict)
        self.assertEqual(response.data['homework']['course']['id'], course.pk)
        self.assertEqual(response.data['homework']['course']['title'], course.title)

    def test_get_reminders_returns_nested_homework_with_category(self):
        """Verify that GET /reminders/ returns nested homework with category object, not just ID."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        homework = homeworkhelper.given_homework_exists(course, category=category)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework)

        # WHEN
        response = self.client.get(reverse('planner_reminders_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        reminder_data = response.data[0]
        # Verify homework is a nested object, not just an ID
        self.assertIsInstance(reminder_data['homework'], dict)
        self.assertEqual(reminder_data['homework']['id'], homework.pk)

        # Verify category is nested within homework as an object, not just an ID
        self.assertIsInstance(reminder_data['homework']['category'], dict)
        self.assertEqual(reminder_data['homework']['category']['id'], category.pk)
        self.assertEqual(reminder_data['homework']['category']['title'], category.title)

    def test_get_reminder_by_id_returns_nested_homework_with_category(self):
        """Verify that GET /reminders/{id}/ returns nested homework with category object."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        homework = homeworkhelper.given_homework_exists(course, category=category)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework)

        # WHEN
        response = self.client.get(reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify homework is a nested object, not just an ID
        self.assertIsInstance(response.data['homework'], dict)
        self.assertEqual(response.data['homework']['id'], homework.pk)

        # Verify category is nested within homework as an object, not just an ID
        self.assertIsInstance(response.data['homework']['category'], dict)
        self.assertEqual(response.data['homework']['category']['id'], category.pk)
        self.assertEqual(response.data['homework']['category']['title'], category.title)

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        reminder1 = reminderhelper.given_reminder_exists(user, event=event)
        reminder2 = reminderhelper.given_reminder_exists(user, event=event)
        reminder3 = reminderhelper.given_reminder_exists(user, event=event)

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Reminder.objects.filter(pk=reminder1.pk).update(updated_at=old_time)
        Reminder.objects.filter(pk=reminder2.pk).update(updated_at=recent_time)
        Reminder.objects.filter(pk=reminder3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_reminders_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(reminder2.pk, returned_ids)
        self.assertIn(reminder3.pk, returned_ids)
        self.assertNotIn(reminder1.pk, returned_ids)

    def test_create_course_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        # Create a course that spans into the future so we can find the next occurrence
        course = coursehelper.given_course_exists(
            course_group,
            start_date=(timezone.now() - timedelta(days=7)).date(),
            end_date=(timezone.now() + timedelta(days=30)).date()
        )
        # Create a schedule with classes on Monday, Wednesday, Friday at 10:00 AM
        courseschedulehelper.given_course_schedule_exists(
            course,
            days_of_week='0101010',
            mon_start_time=datetime.time(10, 0, 0),
            wed_start_time=datetime.time(10, 0, 0),
            fri_start_time=datetime.time(10, 0, 0)
        )

        # WHEN
        data = {
            'title': 'Class reminder',
            'message': 'Time to go to class!',
            'offset': 30,
            'offset_type': enums.MINUTES,
            'type': enums.PUSH,
            'course': course.pk,
            'repeating': True,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reminder.objects.count(), 1)
        reminder = Reminder.objects.get(pk=response.data['id'])
        self.assertEqual(reminder.course.pk, course.pk)
        self.assertTrue(reminder.repeating)
        self.assertFalse(reminder.sent)
        self.assertFalse(reminder.dismissed)
        self.assertIsNotNone(reminder.start_of_range)
        # start_of_range must equal next_class_start - offset (30 min)
        user_tz = pytz.timezone(user.settings.time_zone)
        next_class_start_utc = reminder.start_of_range + timedelta(minutes=30)
        next_class_start_local = next_class_start_utc.astimezone(user_tz)
        self.assertEqual(next_class_start_local.time().replace(second=0, microsecond=0), datetime.time(10, 0, 0))

    def test_create_course_reminder_no_future_occurrence(self):
        """Course with no future class sessions: reminder is created with start_of_range=None."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2020, 1, 6),
            end_date=datetime.date(2020, 5, 8)
        )
        courseschedulehelper.given_course_schedule_exists(
            course,
            days_of_week='0101010',
            mon_start_time=datetime.time(10, 0, 0),
            wed_start_time=datetime.time(10, 0, 0),
            fri_start_time=datetime.time(10, 0, 0)
        )

        # WHEN
        data = {
            'title': 'Class reminder',
            'message': 'Time to go to class!',
            'offset': 30,
            'offset_type': enums.MINUTES,
            'type': enums.PUSH,
            'course': course.pk,
            'repeating': True,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN: created successfully but inactive (no qualifying future occurrence)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reminder = Reminder.objects.get(pk=response.data['id'])
        self.assertIsNone(reminder.start_of_range)
        self.assertIsNone(response.data['start_of_range'])

    def test_create_reminder_course_and_homework_fails(self):
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
            'course': course.pk,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Only one of', response.data['non_field_errors'][0])

    def test_create_event_reminder_with_repeating_fails(self):
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
            'repeating': True,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('repeating', response.data['non_field_errors'][0].lower())

    def test_course_reminder_skips_group_exception(self):
        """Verify that course reminders skip dates in the course group's exceptions."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # Find the next Monday from today (including today if it's Monday)
        # Use the user's timezone to match the implementation in Reminder._get_next_course_occurrence_start
        user_tz = pytz.timezone(user.settings.time_zone)
        today = datetime.datetime.now(user_tz).date()
        days_until_monday = (7 - today.weekday()) % 7
        next_monday = today + timedelta(days=days_until_monday)
        following_monday = next_monday + timedelta(days=7)

        # Set the next Monday as an exception at the group level
        course_group.exceptions = next_monday.strftime('%Y%m%d')
        course_group.save()

        # Create a course that spans both Mondays
        course = coursehelper.given_course_exists(
            course_group,
            start_date=today,
            end_date=following_monday + timedelta(days=1)
        )
        # Schedule on Mondays only
        courseschedulehelper.given_course_schedule_exists(
            course,
            days_of_week='0100000',
            mon_start_time=datetime.time(10, 0, 0)
        )

        # WHEN
        data = {
            'title': 'Class reminder',
            'message': 'Time to go to class!',
            'offset': 30,
            'offset_type': enums.MINUTES,
            'type': enums.PUSH,
            'course': course.pk,
            'repeating': True,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reminder = Reminder.objects.get(pk=response.data['id'])
        # The reminder should skip the first Monday (exception) and target the following Monday.
        # start_of_range = class_start (10:00 local) - offset (30 min), stored in UTC.
        expected_class_start = user_tz.localize(
            datetime.datetime.combine(following_monday, datetime.time(10, 0, 0)))
        expected_start_of_range = (expected_class_start - timedelta(minutes=30)).astimezone(pytz.utc)
        self.assertEqual(reminder.start_of_range, expected_start_of_range)

    def test_course_reminder_skips_course_exception(self):
        """Verify that course reminders skip dates in the course's own exceptions."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # Find the next Monday from today (including today if it's Monday)
        # Use the user's timezone to match the implementation in Reminder._get_next_course_occurrence_start
        user_tz = pytz.timezone(user.settings.time_zone)
        today = datetime.datetime.now(user_tz).date()
        days_until_monday = (7 - today.weekday()) % 7
        next_monday = today + timedelta(days=days_until_monday)
        following_monday = next_monday + timedelta(days=7)

        # Create a course with the next Monday as an exception
        course = coursehelper.given_course_exists(
            course_group,
            start_date=today,
            end_date=following_monday + timedelta(days=1)
        )
        course.exceptions = next_monday.strftime('%Y%m%d')
        course.save()

        # Schedule on Mondays only
        courseschedulehelper.given_course_schedule_exists(
            course,
            days_of_week='0100000',
            mon_start_time=datetime.time(10, 0, 0)
        )

        # WHEN
        data = {
            'title': 'Class reminder',
            'message': 'Time to go to class!',
            'offset': 30,
            'offset_type': enums.MINUTES,
            'type': enums.PUSH,
            'course': course.pk,
            'repeating': True,
        }
        response = self.client.post(reverse('planner_reminders_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reminder = Reminder.objects.get(pk=response.data['id'])
        # The reminder should skip the first Monday (exception) and target the following Monday.
        # start_of_range = class_start (10:00 local) - offset (30 min), stored in UTC.
        expected_class_start = user_tz.localize(
            datetime.datetime.combine(following_monday, datetime.time(10, 0, 0)))
        expected_start_of_range = (expected_class_start - timedelta(minutes=30)).astimezone(pytz.utc)
        self.assertEqual(reminder.start_of_range, expected_start_of_range)

    def test_filter_id_cannot_access_other_users_data(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)
        reminder = reminderhelper.given_reminder_exists(user1, event=event)

        # WHEN
        response = self.client.get(reverse('planner_reminders_list') + f'?id={reminder.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_by_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group,
                                                   start_date=(timezone.now() - timedelta(days=7)).date(),
                                                   end_date=(timezone.now() + timedelta(days=30)).date())
        course2 = coursehelper.given_course_exists(course_group,
                                                   start_date=(timezone.now() - timedelta(days=7)).date(),
                                                   end_date=(timezone.now() + timedelta(days=30)).date())
        courseschedulehelper.given_course_schedule_exists(course1, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        courseschedulehelper.given_course_schedule_exists(course2, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminderhelper.given_reminder_exists(user, course=course1)
        reminderhelper.given_reminder_exists(user, course=course1)
        reminderhelper.given_reminder_exists(user, course=course2)

        # WHEN
        response = self.client.get(reverse('planner_reminders_list') + f'?course={course1.pk}',
                                   HTTP_X_CLIENT_VERSION='3.5.0')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for reminder_data in response.data:
            self.assertIsInstance(reminder_data['course'], dict)
            self.assertEqual(reminder_data['course']['id'], course1.pk)

    def test_course_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1,
                                                   start_date=(timezone.now() - timedelta(days=7)).date(),
                                                   end_date=(timezone.now() + timedelta(days=30)).date())
        course2 = coursehelper.given_course_exists(course_group2)
        courseschedulehelper.given_course_schedule_exists(course1, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminder = reminderhelper.given_reminder_exists(user1, course=course1)

        # WHEN
        responses = [
            self.client.post(reverse('planner_reminders_list'),
                             json.dumps({'course': course2.pk}),
                             content_type='application/json'),
            self.client.put(
                reverse('planner_reminders_detail', kwargs={'pk': reminder.pk}),
                json.dumps({'course': course2.pk}),
                content_type='application/json'),
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
