"""
Tests for ExternalCalendar interaction.
"""
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseExternalCalendar(TestCase):
    def test_externalcalendar_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.get(reverse('api_feed_externalcalendars_lc'))
        response2 = self.client.get(reverse('api_feed_externalcalendars_detail', kwargs={'pk': 1}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_externalcalendars(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        externalcalendarhelper.given_external_calendar_exists(user1)
        externalcalendarhelper.given_external_calendar_exists(user2)
        externalcalendarhelper.given_external_calendar_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_feed_externalcalendars_lc'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ExternalCalendar.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_externalcalendar(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'url': 'http://go.com',
            'color': '#7bd148',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('api_feed_externalcalendars_lc'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ExternalCalendar.objects.count(), 1)
        external_calendar = ExternalCalendar.objects.get(pk=response.data['id'])
        data.update({'user': user.pk})
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, response.data)

    def test_get_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)

        # WHEN
        response = self.client.get(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar, response.data)

    def test_update_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        self.assertEqual(external_calendar.title, '')
        self.assertTrue(external_calendar.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False,
            # Intentionally NOT changing these value
            'url': external_calendar.url
        }
        response = self.client.put(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['shown_on_calendar'], data['shown_on_calendar'])
        external_calendar = ExternalCalendar.objects.get(id=external_calendar.id)
        self.assertEqual(external_calendar.title, data['title'])
        self.assertEqual(external_calendar.shown_on_calendar, data['shown_on_calendar'])

    def test_delete_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        externalcalendarhelper.given_external_calendar_exists(user)

        # WHEN
        response = self.client.delete(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ExternalCalendar.objects.filter(pk=external_calendar.pk).exists())
        self.assertEqual(ExternalCalendar.objects.count(), 1)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user1)

        # WHEN
        response1 = self.client.get(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))
        response2 = self.client.put(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))
        response3 = self.client.delete(
            reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(ExternalCalendar.objects.filter(pk=external_calendar.pk).exists())
        self.assertEqual(ExternalCalendar.objects.count(), 1)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user2)

        # WHEN
        data = {
            'user': user1.pk,
            # Intentionally NOT changing these value
            'url': external_calendar.url
        }
        response = self.client.put(reverse('api_feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(external_calendar.user.pk, user2.pk)
