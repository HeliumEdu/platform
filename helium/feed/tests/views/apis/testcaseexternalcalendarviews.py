__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import os
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.helpers import commonhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper, icalfeedhelper


class TestCaseExternalCalendarViews(APITestCase):
    def test_externalcalendar_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('feed_externalcalendars_list')),
            self.client.post(reverse('feed_externalcalendars_list')),
            self.client.get(reverse('feed_externalcalendars_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('feed_externalcalendars_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_externalcalendars(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        externalcalendarhelper.given_external_calendar_exists(user1)
        externalcalendarhelper.given_external_calendar_exists(user2)
        externalcalendarhelper.given_external_calendar_exists(user2)

        # WHEN
        response = self.client.get(reverse('feed_externalcalendars_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ExternalCalendar.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_create_externalcalendar(self, mock_validate_url):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'url': 'http://go.com/valid-ical-feed',
            'color': '#7bd148',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('feed_externalcalendars_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ExternalCalendar.objects.count(), 1)
        external_calendar = ExternalCalendar.objects.get(pk=response.data['id'])
        data.update({'user': user.pk})
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, data)
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, response.data)

    def test_get_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)

        # WHEN
        response = self.client.get(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, response.data)

    def test_update_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        self.assertEqual(external_calendar.title, '📅 My Calendar')
        self.assertTrue(external_calendar.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False,
            # Intentionally NOT changing these value
            'url': external_calendar.url
        }
        response = self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        external_calendar.refresh_from_db()
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, response.data)

    def test_delete_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        externalcalendarhelper.given_external_calendar_exists(user)

        # WHEN
        response = self.client.delete(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExternalCalendar.objects.filter(pk=external_calendar.pk).exists())
        self.assertEqual(ExternalCalendar.objects.count(), 1)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk})),
            self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk})),
            self.client.delete(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk})),
        ]

        # THEN
        self.assertTrue(ExternalCalendar.objects.filter(pk=external_calendar.pk, user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user2)

        # WHEN
        data = {
            'user': user1.pk,
            # Intentionally NOT changing these value
            'title': external_calendar.title,
            'url': external_calendar.url
        }
        response = self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(external_calendar.user.pk, user2.pk)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_create_invalid_url_disables_calendar(self, mock_urlopen):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        commonhelper.given_urlopen_response_value(status.HTTP_404_NOT_FOUND, mock_urlopen)

        # WHEN
        data = {
            'title': 'some title',
            'url': 'http://www.not-a-valid-ical-url.com/nope',
            'color': '#7bd148',
            'shown_on_calendar': True
        }
        response = self.client.post(reverse('feed_externalcalendars_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], data['url'])
        self.assertFalse(response.data['shown_on_calendar'])

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_update_invalid_url_disables_calendar(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        commonhelper.given_urlopen_response_value(status.HTTP_404_NOT_FOUND, mock_urlopen)

        # WHEN
        data = {
            'url': 'http://www.not-a-valid-ical-url.com/nope',
            # Intentionally NOT changing these value
            'title': external_calendar.title
        }
        response = self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['url'], data['url'])
        self.assertFalse(response.data['shown_on_calendar'])

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_create_invalid_ical(self, mock_urlopen):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'bad.ical'), mock_urlopen)

        # WHEN
        data = {
            'title': 'some title',
            'url': 'http://www.example.com/bad-ical',
            'color': '#7bd148',
            'shown_on_calendar': True
        }
        response = self.client.post(reverse('feed_externalcalendars_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['url'], data['url'])
        self.assertFalse(response.data['shown_on_calendar'])

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_update_invalid_ical(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'bad.ical'), mock_urlopen)

        # WHEN
        data = {
            'url': 'http://www.example.com/bad-ical',
            # Intentionally NOT changing these value
            'title': external_calendar.title
        }
        response = self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['url'], data['url'])
        self.assertFalse(response.data['shown_on_calendar'])

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        responses = [
            self.client.get(reverse('feed_externalcalendars_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('feed_externalcalendars_detail', kwargs={'pk': '9999'}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('matches the given query', response.data['detail'].lower())
