from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.models import UserProfile, UserSettings
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.5'


class TestCaseAuthenticationViews(TestCase):
    def test_password_reset(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        response = self.client.post(reverse('forgot'), {'email': user.email})
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertRedirects(response, '/login')
        temp_pass = response.context['password']

        # WHEN
        response = self.client.post(reverse('login'), {'username': user.get_username(), 'password': temp_pass})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        userhelper.verify_user_logged_in(self)

    def test_password_reset_real_fake_user_same_response(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.post(reverse('forgot'), {'email': user.email})
        status1 = response1.cookies['status_msg'].value
        response2 = self.client.post(reverse('forgot'), {'email': 'fake@fake.com'})
        status2 = response2.cookies['status_msg'].value

        # WHEN
        self.assertIn('been emailed a temporary password', status1)
        self.assertEqual(status1, status2)

    def test_registration_success(self):
        # GIVEN
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('register'),
                                    {'email': 'test@test.com', 'username': 'my_test_user', 'password1': 'test_pass_1!',
                                     'password2': 'test_pass_1!', 'time_zone': 'America/Chicago'})

        # THEN
        userhelper.verify_user_not_logged_in(self)
        user = get_user_model().objects.get(email='test@test.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.username, 'my_test_user')
        self.assertEqual(user.settings.time_zone, 'America/Chicago')
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('verify your email address', str(response.cookies['status_msg']))

        self.assertTrue(UserProfile.objects.filter(user__email='test@test.com').exists())
        self.assertTrue(UserSettings.objects.filter(user__email='test@test.com').exists())

    def test_registration_bad_data(self):
        # GIVEN
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('register'),
                                    {'email': 'test@not-a-valid-email', 'username': 'my_test_user',
                                     'password1': 'test_pass_1!', 'password2': 'test_pass_1!',
                                     'time_zone': 'America/Chicago'})

        # THEN
        userhelper.verify_user_not_logged_in(self)
        self.assertFalse(get_user_model().objects.filter(username='my_test_user').exists())
        self.assertContains(response, 'Enter a valid email address.')

    def test_verification_success(self):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()
        user.save()

        # WHEN
        response1 = self.client.post(reverse('login'), {'username': user.get_username(), 'password': 'test_pass_1!'})
        response2 = self.client.get(
            reverse('verify') + '?username={}&code={}'.format(user.username, user.verification_code))

        # THEN
        self.assertContains(response1, 'your account is not active', status_code=status.HTTP_401_UNAUTHORIZED)
        user = get_user_model().objects.get(email=user.email)
        self.assertEqual(response2.status_code, status.HTTP_302_FOUND)
        userhelper.verify_user_logged_in(self)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(user.get_username(), 'test_user')
        self.assertTrue(user.is_active)
