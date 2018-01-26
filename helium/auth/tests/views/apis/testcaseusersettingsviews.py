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


class TestCaseUserSettingsViews(TestCase):
    def test_user_settings_login_required(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_auth_users_settings_detail', kwargs={'pk': user.pk})),
            self.client.put(reverse('api_auth_users_settings_detail', kwargs={'pk': user.pk}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        response = self.client.put(reverse('api_auth_users_settings_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertFalse(response.data['show_getting_started'])
        self.assertEqual(response.data['time_zone'], 'America/Chicago')
        user = get_user_model().objects.get(pk=user.id)
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(user.settings.time_zone, response.data['time_zone'])

    def test_put_bad_data_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'time_zone': 'invalid'
        }
        response = self.client.put(reverse('api_auth_users_settings_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

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
        response = self.client.put(reverse('api_auth_users_settings_detail', kwargs={'pk': user.pk}), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.settings.private_slug, private_slug)

    def test_unsubscribe_admin_emails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertTrue(user.settings.receive_emails_from_admin)

        response1 = self.client.get(reverse('unsubscribe') + '?username={}&code={}'.format(user.username,
                                                                                           user.verification_code))
        response2 = self.client.get(reverse('unsubscribe') + '?username={}&code={}'.format('fake-user',
                                                                                           'fake-verification'))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_302_FOUND)
        user = get_user_model().objects.get(pk=user.id)
        self.assertFalse(user.settings.receive_emails_from_admin)
