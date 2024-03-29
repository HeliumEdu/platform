__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.models import UserProfile
from helium.auth.models import UserSettings
from helium.auth.tests.helpers import userhelper


class TestCaseAuthenticationViews(TestCase):
    def test_password_reset(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        response = self.client.put(reverse('auth_user_resource_forgot'),
                                   json.dumps({'email': user.email}),
                                   content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        temp_pass = response.context['password']

        # THEN
        response = self.client.post(reverse('auth_token_resource_obtain'),
                                    json.dumps({'username': user.get_username(), 'password': temp_pass}),
                                    content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_real_fake_user_same_response(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.put(reverse('auth_user_resource_forgot'),
                                   json.dumps({'email': 'fake@fake.com'}),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_registration_success(self):
        # WHEN
        data = {
            'email': 'test@test.com',
            'username': 'my_test_user',
            'password': 'test_pass_1!',
            'time_zone': 'America/Chicago'}
        response1 = self.client.post(reverse('auth_user_resource_register'),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response1.data['settings']['time_zone'], 'America/Chicago')
        response2 = self.client.post(reverse('auth_token_resource_obtain'),
                                     json.dumps({'username': 'my_test_user', 'password': 'test_pass_1!'}),
                                     content_type='application/json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('account is not active', response2.data['non_field_errors'][0])
        user = get_user_model().objects.get(email='test@test.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, 'my_test_user')
        self.assertEqual(user.settings.time_zone, 'America/Chicago')

        self.assertTrue(UserProfile.objects.filter(user__email='test@test.com').exists())
        self.assertTrue(UserSettings.objects.filter(user__email='test@test.com').exists())

    def test_registration_bad_data(self):
        # WHEN
        response = self.client.post(reverse('auth_user_resource_register'),
                                    json.dumps({'email': 'test@not-a-valid-email', 'username': 'my_test_user',
                                                'password1': 'test_pass_1!', 'password2': 'test_pass_1!',
                                                'time_zone': 'America/Chicago'}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(get_user_model().objects.filter(username='my_test_user').exists())
        self.assertIn('email', response.data)

    def test_verification_success(self):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()

        # WHEN
        response = self.client.get(
            reverse('auth_user_resource_verify') + f'?username={user.username}&code={user.verification_code}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = get_user_model().objects.get(email=user.email)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(user.get_username(), 'test_user')
        self.assertTrue(user.is_active)

    def test_verification_bad_request(self):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()

        # WHEN
        response = self.client.get(
            reverse('auth_user_resource_verify') + f'?code={user.verification_code}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user = get_user_model().objects.get(email=user.email)
        self.assertIn("'username' and 'password' must be given", response.data[0])
        self.assertFalse(user.is_active)

    def test_verification_not_found(self):
        # WHEN
        response = self.client.get(
            reverse('auth_user_resource_verify') + "?username=not-a-user&code=not-a-real-code")

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
