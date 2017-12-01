"""
Tests for User interaction.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from helium.users.tests.helpers import userhelper

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
        self.assertEquals(user.username, response.data['username'])
        self.assertEquals(user.email, response.data['email'])

    def test_username_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEquals(user.email, 'test@heliumedu.com')
        self.assertIsNone(user.email_changing)

        # WHEN
        data = {
            'username': 'new_username',
            'email': user.email
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEquals(response.data['username'], 'new_username')
        self.assertEquals(response.data['email'], 'test@heliumedu.com')
        user = get_user_model().objects.get(id=user.id)
        self.assertEquals(user.username, response.data['username'])
        self.assertEquals(user.email, response.data['email'])
        self.assertIsNone(user.email_changing)

    def test_email_changing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        self.assertEquals(user.email, 'test@heliumedu.com')
        self.assertIsNone(user.email_changing)
        self.assertEquals(user.username, 'test_user')

        # WHEN
        data = {
            'username': user.username,
            'email': 'new@email.com'
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEquals(response.data['username'], user.username)
        self.assertEquals(response.data['email'], user.email)
        self.assertEquals(response.data['email_changing'], 'new@email.com')
        user = get_user_model().objects.get(id=user.id)
        self.assertEquals(user.email, response.data['email'])
        self.assertEquals(user.email_changing, response.data['email_changing'])
        self.assertEquals(user.username, response.data['username'])

    def test_email_changes_after_verification(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user.email_changing = 'new@email.com'
        user.verification_code = 'moo-moo-moo'
        user.save()

        self.client.get(reverse('verify') + '?username={}&code={}'.format(user.username, user.verification_code))

        # THEN
        user = get_user_model().objects.get(id=user.id)
        self.assertEquals(user.email, 'new@email.com')
        self.assertIsNone(user.email_changing)

    def test_username_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            'username': user1.username,
            'email': user2.email
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEquals(response.status_code, 400)
        self.assertIn('username', response.data)

    def test_email_already_exists(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')

        # WHEN
        data = {
            'username': user2.username,
            'email': user1.email
        }
        response = self.client.put(reverse('api_user'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEquals(response.status_code, 400)
        self.assertIn('email', response.data)
