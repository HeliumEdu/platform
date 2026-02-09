__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
from urllib.parse import quote

import pytz
from dateutil import parser
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Event
from helium.planner.tests.helpers import eventhelper


class TestCaseEventViews(APITestCase):
    def test_event_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_list')),
            self.client.post(reverse('planner_events_list')),
            self.client.get(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_events(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)

        # WHEN
        response = self.client.get(reverse('planner_events_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'priority': 75,
            'comments': 'some comment',
            'owner_id': '12345',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])
        eventhelper.verify_event_matches_data(self, event, data)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_create_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00-0500',
            'end': '2014-05-08T14:00:00-0500',
            'priority': 75,
            'comments': 'some comment',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])
        self.assertEqual(event.start.isoformat(), parser.parse(data['start']).astimezone(timezone.utc).isoformat())
        self.assertEqual(event.end.isoformat(), parser.parse(data['end']).astimezone(timezone.utc).isoformat())

    def test_create_assumes_naive_datetime_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08 12:00:00',
            'end': '2014-05-08 14:00:00',
            'priority': 75,
            'comments': 'some comment',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])

        start = timezone.make_aware(parser.parse(data['start']), timezone.utc)
        end = timezone.make_aware(parser.parse(data['end']), timezone.utc)
        self.assertEqual(event.start.isoformat(), start.isoformat())
        self.assertEqual(event.end.isoformat(), end.isoformat())

    def test_get_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(reverse('planner_events_detail',
                                           kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_update_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        self.assertEqual(event.title, '🏀 Test Event')

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-08T14:00:00Z',
            'priority': 12,
            'comments': 'some comment',
            'owner_id': '54321'
        }
        response = self.client.put(reverse('planner_events_detail',
                                           kwargs={'pk': event.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        event.refresh_from_db()
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_update_start_before_end_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-07T14:00:00Z',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('must be before', response.data['non_field_errors'][0])

    def test_patch_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00-0500',
            'end': '2016-05-08T14:00:00-0500',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start.isoformat(), parser.parse(data['start']).astimezone(timezone.utc).isoformat())
        self.assertEqual(event.end.isoformat(), parser.parse(data['end']).astimezone(timezone.utc).isoformat())

    def test_patch_assumes_naive_datetime_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/New_York'
        user.settings.save()
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': '2016-05-08 12:00:00',
            'end': '2016-05-08 14:00:00',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()

        start = timezone.make_aware(parser.parse(data['start']), pytz.utc)
        end = timezone.make_aware(parser.parse(data['end']), pytz.utc)
        self.assertEqual(event.start.isoformat(), start.isoformat())
        self.assertEqual(event.end.isoformat(), end.isoformat())

    def test_delete_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.delete(reverse('planner_events_detail',
                                              kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())
        self.assertEqual(Event.objects.count(), 0)

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_detail', kwargs={'pk': event.pk})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': event.pk})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': event.pk}))
        ]

        # THEN
        self.assertTrue(Event.objects.filter(pk=event.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.put(reverse('planner_events_detail', kwargs={'pk': event.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_not_found(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': '9999'}))
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
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2017, 5, 8, 16, 0, 0, tzinfo=timezone.utc),
                                       end=datetime.datetime(2017, 5, 8, 16, 59, 0, tzinfo=timezone.utc))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2017, 5, 8, 17, 0, 0, tzinfo=timezone.utc),
                                                end=datetime.datetime(2017, 5, 8, 18, 0, 0, tzinfo=timezone.utc))
        event4 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2017, 5, 8, 19, 30, 0, tzinfo=timezone.utc),
                                                end=datetime.datetime(2017, 5, 8, 20, 0, 0, tzinfo=timezone.utc))
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2017, 5, 8, 20, 1, 0, tzinfo=timezone.utc),
                                       end=datetime.datetime(2017, 5, 8, 21, 0, 0, tzinfo=timezone.utc))

        # WHEN
        response = self.client.get(
            reverse(
                'planner_events_list') + f'?from={quote(event2.start.isoformat())}&to={quote(event4.end.isoformat())}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_range_query_multiday(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2025, 10, 31, 0, 0, 0, tzinfo=timezone.utc),
                                       end=datetime.datetime(2025, 11, 2, 0, 0, 0, tzinfo=timezone.utc))

        # WHEN
        response = self.client.get(
            reverse(
                'planner_events_list') + f'?from=2025-11-01T00:00:00Z&to=2025-11-02T00:00:00Z')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_title_search_query(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user, title='test1')
        eventhelper.given_event_exists(user, title='test2')

        # WHEN
        response = self.client.get(reverse('planner_events_list') + '?search=tEst1')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], event.title)

    def test_events_for_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)
        self.assertEqual(Event.objects.count(), 4)

        # WHEN
        response = self.client.delete(reverse('planner_events_resource_delete'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.for_user(user2.pk).count(), 0)
