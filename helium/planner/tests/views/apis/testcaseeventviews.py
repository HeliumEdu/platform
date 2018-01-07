import datetime
import json
from urllib.parse import quote

from django.utils import timezone
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Event
from helium.planner.tests.helpers import eventhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseEventViews(TestCase):
    def test_event_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_events_list')),
            self.client.post(reverse('api_planner_events_list')),
            self.client.get(reverse('api_planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_events_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_events(self):
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_planner_events_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'priority': 75,
            'comments': 'some comment',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('api_planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])
        eventhelper.verify_event_matches_data(self, event, data)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_get_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(reverse('api_planner_events_detail',
                                           kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_update_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-08T14:00:00Z',
            'priority': 12,
            'comments': 'some comment'
        }
        response = self.client.put(reverse('api_planner_events_detail',
                                           kwargs={'pk': event.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        event = Event.objects.get(pk=event.pk)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_delete_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.delete(reverse('api_planner_events_detail',
                                              kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())
        self.assertEqual(Event.objects.count(), 0)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_events_detail', kwargs={'pk': event.pk})),
            self.client.put(reverse('api_planner_events_detail', kwargs={'pk': event.pk})),
            self.client.delete(reverse('api_planner_events_detail', kwargs={'pk': event.pk}))
        ]

        # THEN
        self.assertTrue(Event.objects.filter(pk=event.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.post(reverse('api_planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.put(reverse('api_planner_events_detail', kwargs={'pk': event.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_events_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2014, 5, 8, 16, 0, 0, tzinfo=timezone.utc),
                                       end=datetime.datetime(2014, 5, 8, 17, 0, 0, tzinfo=timezone.utc))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2014, 5, 8, 17, 0, 0, tzinfo=timezone.utc),
                                                end=datetime.datetime(2014, 5, 8, 18, 0, 0, tzinfo=timezone.utc))
        event3 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2014, 5, 8, 18, 30, 0, tzinfo=timezone.utc),
                                                end=datetime.datetime(2014, 5, 8, 19, 0, 0, tzinfo=timezone.utc))
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2014, 5, 8, 19, 30, 0, tzinfo=timezone.utc),
                                       end=datetime.datetime(2014, 5, 8, 21, 0, 0, tzinfo=timezone.utc))

        response = self.client.get(
            reverse('api_planner_events_list') + '?start={}&end={}'.format(quote(event2.start.isoformat()),
                                                                          quote(event3.end.isoformat())))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_title_search_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        event = eventhelper.given_event_exists(user, title='test1')
        eventhelper.given_event_exists(user, title='test2')

        response = self.client.get(reverse('api_planner_events_list') + '?search=test1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], event.title)
