"""
Tests for authentication.
"""
import json
import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from helium.users.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserAuthentication(TestCase):
    def test_user_settings_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.get(reverse('api_user_settings'))

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login?next={}'.format(reverse('api_user_settings')))

    def test_get_user_settings(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.get(reverse('api_user_settings'))

        # THEN
        self.assertEquals(user.settings.default_view, response.data['default_view'])
        self.assertEquals(user.settings.week_starts_on, response.data['week_starts_on'])
        self.assertEquals(user.settings.all_day_offset, response.data['all_day_offset'])
        self.assertEquals(user.settings.show_getting_started, response.data['show_getting_started'])
        self.assertEquals(user.settings.events_color, response.data['events_color'])
        self.assertEquals(user.settings.default_reminder_offset, response.data['default_reminder_offset'])
        self.assertEquals(user.settings.default_reminder_offset_type, response.data['default_reminder_offset_type'])
        self.assertEquals(user.settings.default_reminder_type, response.data['default_reminder_type'])
        self.assertEquals(user.settings.receive_emails_from_admin, response.data['receive_emails_from_admin'])
        self.assertEquals(user.settings.events_private_slug, response.data['events_private_slug'])
        self.assertEquals(user.settings.private_slug, response.data['private_slug'])

    def test_put_user_setting(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertTrue(user.settings.show_getting_started)
        self.assertEquals(user.settings.time_zone, 'America/Los_Angeles')

        # WHEN
        data = {
            'show_getting_started': False,
            'time_zone': 'America/Chicago'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertFalse(response.data['show_getting_started'])
        self.assertEquals(response.data['time_zone'], 'America/Chicago')
        user = get_user_model().objects.get(id=user.id)
        self.assertFalse(user.settings.show_getting_started)
        self.assertEquals(user.settings.time_zone, response.data['time_zone'])

    def test_put_bad_data_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'time_zone': 'invalid'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEquals(response.status_code, 400)
        self.assertIn('time_zone', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        private_slug = str(uuid.uuid4)
        user.settings.private_slug = private_slug
        user.settings.save()

        # WHEN
        data = {
            'private_slug': 'new_slug'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        user = get_user_model().objects.get(id=user.id)
        self.assertEquals(response.status_code, 200)
        self.assertEquals(user.settings.private_slug, private_slug)
