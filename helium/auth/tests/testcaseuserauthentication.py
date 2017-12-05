"""
Tests for authentication.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from helium.auth.models import UserProfile, UserSettings
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUserAuthentication(TestCase):
    def test_login_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('login'), {'username': user.get_username(), 'password': 'test_pass_1!'})

        # THEN
        self.assertEqual(response.status_code, 302)
        userhelper.verify_user_logged_in(self)

    def test_logout_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.client.post(reverse('login'), {'username': user.get_username(), 'password': 'test_pass_1!'})

        # WHEN
        response = self.client.post('/logout')

        # THEN
        self.assertEqual(response.status_code, 302)
        userhelper.verify_user_not_logged_in(self)

    def test_login_failure_wrong_password(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('login'), {'username': user.get_username(), 'password': 'wrong_pass'})

        # THEN
        self.assertEqual(response.status_code, 401)
        userhelper.verify_user_not_logged_in(self)

    def test_password_reset(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        response = self.client.post(reverse('forgot'), {'email': user.email})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login')
        temp_pass = response.context['password']

        # WHEN
        response = self.client.post(reverse('login'), {'username': user.get_username(), 'password': temp_pass})

        # THEN
        self.assertEqual(response.status_code, 302)
        userhelper.verify_user_logged_in(self)

    def test_registration_success(self):
        # GIVEN
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('register'),
                                    {'email': 'test@test.com', 'username': 'my_test_user', 'password1': 'test_pass_1!',
                                     'password2': 'test_pass_1!', 'time_zone': 'America/Chicago'})

        # THEN
        user = get_user_model().objects.get(email='test@test.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, 'my_test_user')
        self.assertEqual(user.settings.time_zone, 'America/Chicago')
        self.assertEqual(response.status_code, 302)
        self.assertIn('verify your email address', str(response.cookies['status_msg']))

        self.assertTrue(UserProfile.objects.filter(user__email='test@test.com').exists())
        self.assertTrue(UserSettings.objects.filter(user__email='test@test.com').exists())

    def test_verification_success(self):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()
        user.save()

        # WHEN
        response = self.client.get(reverse('verify') + '?username={}&code={}'.format(user.username, user.verification_code))

        # THEN
        user = get_user_model().objects.get(email='test@heliumedu.com')
        self.assertEqual(response.status_code, 302)
        userhelper.verify_user_logged_in(self)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(user.get_username(), 'test_user')
        self.assertTrue(user.is_active)
