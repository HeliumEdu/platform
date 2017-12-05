"""
Tests for ExternalCalendar interaction.
"""
import json

from django.test import TestCase
from django.urls import reverse

from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserAuthentication(TestCase):
    def test_externalcalendar_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.get(reverse('api_feed_externalcalendar_list'))
        response2 = self.client.get(reverse('api_feed_externalcalendar_detail', kwargs={'pk': 1}))

        # THEN
        self.assertEqual(response1.status_code, 302)
        self.assertRedirects(response1, '/login?next={}'.format(reverse('api_feed_externalcalendar_list')))
        self.assertEqual(response2.status_code, 302)
        self.assertRedirects(response2, '/login?next={}'.format(reverse('api_feed_externalcalendar_detail', kwargs={'pk': 1})))

    def test_get_externalcalendars(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        externalcalendarhelper.given_external_calendar(user1)
        externalcalendarhelper.given_external_calendar(user2)
        externalcalendarhelper.given_external_calendar(user2)

        # WHEN
        response = self.client.get(reverse('api_feed_externalcalendar_list'))

        # THEN
        self.assertEqual(len(response.data), 2)

    def test_post_externalcalendar(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'url': 'http://go.com',
            'color': '#f552',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('api_feed_externalcalendar_list'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 201)
        self.assertEqual(ExternalCalendar.objects.count(), 1)
        externalcalendar = ExternalCalendar.objects.get(pk=response.data['id'])
        self.assertEqual(externalcalendar.title, 'some title')
        self.assertEqual(externalcalendar.url, 'http://go.com')
        self.assertEqual(externalcalendar.color, '#f552')
        self.assertEqual(externalcalendar.shown_on_calendar, False)
        self.assertEqual(externalcalendar.user.pk, user.pk)

    def test_get_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        externalcalendar = externalcalendarhelper.given_external_calendar(user)
        externalcalendarhelper.given_external_calendar(user)

        # WHEN
        response = self.client.get(reverse('api_feed_externalcalendar_detail', kwargs={'pk': externalcalendar.pk}))

        # THEN
        self.assertEqual(externalcalendar.title, response.data['title'])
        self.assertEqual(externalcalendar.url, response.data['url'])
        self.assertEqual(externalcalendar.color, response.data['color'])
        self.assertEqual(externalcalendar.shown_on_calendar, response.data['shown_on_calendar'])
        self.assertEqual(externalcalendar.user.pk, response.data['user'])

    def test_put_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        externalcalendar = externalcalendarhelper.given_external_calendar(user)
        self.assertEqual(externalcalendar.title, '')
        self.assertTrue(externalcalendar.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False,
            # Intentionally NOT changing this value
            'url': externalcalendar.url
        }
        response = self.client.put(reverse('api_feed_externalcalendar_detail', kwargs={'pk': externalcalendar.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.data['title'], 'new title')
        self.assertEqual(response.data['url'], externalcalendar.url)
        self.assertFalse(response.data['shown_on_calendar'])
        externalcalendar = ExternalCalendar.objects.get(id=externalcalendar.id)
        self.assertEqual(externalcalendar.title, response.data['title'])
        self.assertFalse(externalcalendar.shown_on_calendar, response.data['shown_on_calendar'])

    def test_delete_externalcalendar_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        externalcalendar = externalcalendarhelper.given_external_calendar(user)
        externalcalendarhelper.given_external_calendar(user)

        # WHEN
        self.client.delete(reverse('api_feed_externalcalendar_detail', kwargs={'pk': externalcalendar.pk}))

        # THEN
        self.assertFalse(ExternalCalendar.objects.filter(pk=externalcalendar.pk).exists())
        self.assertEqual(ExternalCalendar.objects.count(), 1)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        externalcalendar = externalcalendarhelper.given_external_calendar(user1)

        # WHEN
        response = self.client.delete(reverse('api_feed_externalcalendar_detail', kwargs={'pk': externalcalendar.pk}))

        # THEN
        self.assertEqual(response.status_code, 404)
        self.assertTrue(ExternalCalendar.objects.filter(pk=externalcalendar.pk).exists())
        self.assertEqual(ExternalCalendar.objects.count(), 1)
