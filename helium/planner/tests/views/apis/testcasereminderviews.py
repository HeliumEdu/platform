__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

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
        self.assertIsNotNone(reminder.start_of_range)

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
        today = timezone.now().date()
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
        # The reminder should skip the first Monday (exception) and target the following Monday
        self.assertEqual(reminder.start_of_range.date(), following_monday)

    def test_course_reminder_skips_course_exception(self):
        """Verify that course reminders skip dates in the course's own exceptions."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # Find the next Monday from today (including today if it's Monday)
        today = timezone.now().date()
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
        # The reminder should skip the first Monday (exception) and target the following Monday
        self.assertEqual(reminder.start_of_range.date(), following_monday)
