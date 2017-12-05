"""
Tests for User interaction.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from helium.auth.models import UserSettings, UserProfile
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseUser(TestCase):
    def test_user_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self.client.get(reverse('api_user'))

        # THEN
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, '/login?next={}'.format(reverse('api_user')))

    def test_get_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        response = self.client.get(reverse('api_user'))

        # THEN
        self.assertNotIn('verification_code', response.data)
        self.assertEqual(user.username, response.data['username'])
        self.assertEqual(user.email, response.data['email'])

    def test_username_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEqual(user.email, 'test@heliumedu.com')
        self.assertIsNone(user.email_changing)

        # WHEN
        data = {
            'username': 'new_username',
            # Intentionally NOT changing this value
            'email': user.email
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.data['username'], 'new_username')
        self.assertEqual(response.data['email'], 'test@heliumedu.com')
        user = get_user_model().objects.get(id=user.id)
        self.assertEqual(user.username, response.data['username'])
        self.assertEqual(user.email, response.data['email'])
        self.assertIsNone(user.email_changing)

    def test_email_changing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEqual(user.email, 'test@heliumedu.com')
        self.assertIsNone(user.email_changing)
        self.assertEqual(user.username, 'test_user')

        # WHEN
        data = {
            'email': 'new@email.com',
            # Intentionally NOT changing this value
            'username': user.username
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.data['username'], user.username)
        self.assertEqual(response.data['email'], user.email)
        self.assertEqual(response.data['email_changing'], 'new@email.com')
        user = get_user_model().objects.get(id=user.id)
        self.assertEqual(user.email, response.data['email'])
        self.assertEqual(user.email_changing, response.data['email_changing'])
        self.assertEqual(user.username, response.data['username'])

    def test_email_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.email_changing = 'new@email.com'
        user.verification_code = 'moo-moo-moo'
        user.save()

        self.client.get(reverse('verify') + '?username={}&code={}'.format(user.username, user.verification_code))

        # THEN
        user = get_user_model().objects.get(id=user.id)
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
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, 204)
        user = get_user_model().objects.get(id=user.id)
        self.assertTrue(user.check_password('new_pass_1!'))

    def test_password_change_fails_missing_old_new_pass(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # THEN
        data = {
            'old_password': '',
            'new_password1': 'new_pass_1!',
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, 400)
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
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, 400)
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
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, 400)
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
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # WHEN
        self.assertEqual(response.status_code, 400)
        self.assertIn('new_password2', response.data)

    def test_username_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            # Trying to change username to match user1's email
            'username': user1.username,
            'email': user2.email
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_email_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            # Trying to change email to match user1's email
            'email': user1.email,
            'username': user2.username
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 400)
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
        response = self.client.delete(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 204)
        self.assertFalse(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(UserSettings.objects.filter(user__id=user.pk).exists())
        self.assertFalse(UserProfile.objects.filter(user__id=user.pk).exists())

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
        response = self.client.delete(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
