"""
Tests for UserSettings interaction.
"""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserSettings(TestCase):
    def test_user_settings_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.get(reverse('api_user_settings'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, '/login?next={}'.format(reverse('api_user_settings')))

    def test_get_user_settings(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.get(reverse('api_user_settings'))

        # THEN
        self.assertEqual(user.settings.default_view, response.data['default_view'])
        self.assertEqual(user.settings.week_starts_on, response.data['week_starts_on'])
        self.assertEqual(user.settings.all_day_offset, response.data['all_day_offset'])
        self.assertEqual(user.settings.show_getting_started, response.data['show_getting_started'])
        self.assertEqual(user.settings.events_color, response.data['events_color'])
        self.assertEqual(user.settings.default_reminder_offset, response.data['default_reminder_offset'])
        self.assertEqual(user.settings.default_reminder_offset_type, response.data['default_reminder_offset_type'])
        self.assertEqual(user.settings.default_reminder_type, response.data['default_reminder_type'])
        self.assertEqual(user.settings.receive_emails_from_admin, response.data['receive_emails_from_admin'])
        self.assertEqual(user.settings.events_private_slug, response.data['events_private_slug'])
        self.assertEqual(user.settings.private_slug, response.data['private_slug'])
        self.assertEqual(user.settings.user.pk, response.data['user'])

    def test_put_user_setting(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertTrue(user.settings.show_getting_started)
        self.assertEqual(user.settings.time_zone, 'America/Los_Angeles')

        # WHEN
        data = {
            'show_getting_started': False,
            'time_zone': 'America/Chicago'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertFalse(response.data['show_getting_started'])
        self.assertEqual(response.data['time_zone'], 'America/Chicago')
        user = get_user_model().objects.get(id=user.id)
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(user.settings.time_zone, response.data['time_zone'])

    def test_put_bad_data_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'time_zone': 'invalid'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time_zone', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        private_slug = str(uuid.uuid4())
        user.settings.private_slug = private_slug
        user.settings.save()

        # WHEN
        data = {
            'private_slug': 'new_slug'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        user = get_user_model().objects.get(id=user.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(user.settings.private_slug, private_slug)

    def test_unsubscribe_admin_emails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertTrue(user.settings.receive_emails_from_admin)

        self.client.get(reverse('unsubscribe') + '?username={}&code={}'.format(user.username, user.verification_code))

        # THEN
        user = get_user_model().objects.get(id=user.id)
        self.assertFalse(user.settings.receive_emails_from_admin)
