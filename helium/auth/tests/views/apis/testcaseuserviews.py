import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.models import UserSettings, UserProfile
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.6'


class TestCaseUserViews(APITestCase):
    def test_user_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_auth_user_detail')),
            self.client.put(reverse('api_auth_user_detail'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.get(reverse('api_auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('verification_code', response.data)
        self.assertEqual(user.username, response.data['username'])
        self.assertEqual(user.email, response.data['email'])
        self.assertNotIn('phone_verification_code', response.data['profile'])
        self.assertEqual(user.profile.phone, response.data['profile']['phone'])
        self.assertEqual(user.profile.user.pk, response.data['profile']['user'])
        self.assertEqual(user.settings.default_view, response.data['settings']['default_view'])
        self.assertEqual(user.settings.week_starts_on, response.data['settings']['week_starts_on'])
        self.assertEqual(user.settings.all_day_offset, response.data['settings']['all_day_offset'])
        self.assertEqual(user.settings.show_getting_started, response.data['settings']['show_getting_started'])
        self.assertEqual(user.settings.events_color, response.data['settings']['events_color'])
        self.assertEqual(user.settings.default_reminder_offset, response.data['settings']['default_reminder_offset'])
        self.assertEqual(user.settings.default_reminder_offset_type,
                         response.data['settings']['default_reminder_offset_type'])
        self.assertEqual(user.settings.default_reminder_type, response.data['settings']['default_reminder_type'])
        self.assertEqual(user.settings.receive_emails_from_admin,
                         response.data['settings']['receive_emails_from_admin'])
        self.assertEqual(user.settings.private_slug, response.data['settings']['private_slug'])
        self.assertEqual(user.settings.user.pk, response.data['settings']['user'])

    def test_username_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEqual(user.email, 'user@test.com')
        self.assertIsNone(user.email_changing)

        # WHEN
        data = {
            'username': 'new_username',
            # Intentionally NOT changing these value
            'email': user.email
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], data['username'])
        self.assertEqual(response.data['email'], user.email)
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.username, response.data['username'])
        self.assertEqual(user.email, response.data['email'])
        self.assertIsNone(user.email_changing)

    def test_email_changing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEqual(user.email, 'user@test.com')
        self.assertIsNone(user.email_changing)
        self.assertEqual(user.username, 'test_user')

        # WHEN
        data = {
            'email': 'new@email.com',
            # Intentionally NOT changing these value
            'username': user.username
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], user.username)
        self.assertEqual(response.data['email'], user.email)
        self.assertEqual(response.data['email_changing'], 'new@email.com')
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.email, response.data['email'])
        self.assertEqual(user.email_changing, response.data['email_changing'])
        self.assertEqual(user.username, response.data['username'])

    def test_email_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.email_changing = 'new@email.com'
        user.verification_code = 'moo-moo-moo'
        user.save()

        response = self.client.get(
            reverse('verify') + '?username={}&code={}'.format(user.username,
                                                              user.verification_code))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        userhelper.verify_user_logged_in(self)
        user = get_user_model().objects.get(pk=user.id)
        self.assertEqual(user.email, 'new@email.com')
        self.assertIsNone(user.email_changing)

    def test_password_change(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': 'test_pass_1!',
            'new_password1': 'new_pass_1!',
            'new_password2': 'new_pass_1!'
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user = get_user_model().objects.get(pk=user.id)
        userhelper.verify_user_logged_in(self)
        self.assertTrue(user.check_password('new_pass_1!'))

    def test_password_change_fails_missing_old_new_pass(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': '',
            'new_password1': 'new_pass_1!',
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('old_password', response.data)

    def test_password_change_fails_blank_new_pass(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': 'test_pass_1!',
            'new_password1': '',
            'new_password2': '',
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password1', response.data)

    def test_password_change_fails_mismatch(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': 'test_pass_1!',
            'new_password1': 'new_pass_1!',
            'new_password2': 'new_pass_1!oops',
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password2', response.data)

    def test_password_change_fails_to_meet_requirements(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': 'test_pass_1!',
            'new_password1': 'blerg',
            'new_password2': 'blerg',
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password2', response.data)

    def test_username_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            # Trying to change username to match user1's email
            'username': user1.username,
            'email': user2.email
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)

    def test_email_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            # Trying to change email to match user1's email
            'email': user1.email,
            'username': user2.username
        }
        response = self.client.put(reverse('api_auth_user_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_delete_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            # Trying to change email to match user1's email
            'email': user.email,
            'username': user.username,
            'password': 'test_pass_1!'
        }
        response = self.client.delete(reverse('api_auth_user_detail'), json.dumps(data),
                                      content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(UserSettings.objects.filter(user_id=user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(user_id=user.pk).exists())

    def test_delete_fails_bad_request(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            # Trying to change email to match user1's email
            'email': user.email,
            'username': user.username,
            'password': 'wrong_pass'
        }
        response = self.client.delete(reverse('api_auth_user_detail'), json.dumps(data),
                                      content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
