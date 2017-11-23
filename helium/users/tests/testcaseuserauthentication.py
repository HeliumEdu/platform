"""
Tests for authentication.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from helium.users.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


class TestCaseUserAuthentication(TestCase):
    def test_login_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.assertNotIn('_auth_user_id', self.client.session)

        # WHEN
        response = self.client.post('/login', {'username': user.get_username(), 'password': 'test_pass_1!'})

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_logout_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.client.post('/login', {'username': user.get_username(), 'password': 'test_pass_1!'})

        # WHEN
        response = self.client.post('/logout')

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_failure_wrong_password(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.assertNotIn('_auth_user_id', self.client.session)

        # WHEN
        response = self.client.post('/login', {'username': user.get_username(), 'password': 'wrong_pass'})

        # THEN
        self.assertEqual(response.status_code, 401)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_reset(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        response = self.client.post('/forgot', {'email': user.get_username()})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login')
        temp_pass = response.context['password']

        # WHEN
        response = self.client.post('/login', {'username': user.get_username(), 'password': temp_pass})

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)

    def test_registration_success(self):
        # GIVEN
        self.assertNotIn('_auth_user_id', self.client.session)

        # WHEN
        response = self.client.post('/register',
                                    {'email': 'test@test.com', 'password1': 'test_pass_1!',
                                     'password2': 'test_pass_1!', 'first_name': 'first', 'last_name': 'last',
                                     'time_zone': 'US/Pacific'})

        # THEN
        user = get_user_model().objects.get(email='test@test.com')
        self.assertEqual(response.status_code, 302)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEquals(get_user_model().objects.count(), 1)
        self.assertEquals(user.get_username(), 'test@test.com')
