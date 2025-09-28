__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.20"

import json
from datetime import timedelta, datetime

import pytz
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from helium.auth.tests.helpers import userhelper


class TestCaseTokenViews(APITestCase):
    def test_token_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        data = {
            'username': user.get_username(),
            'password': 'test_pass_1!'
        }
        response1 = self.client.post(reverse('auth_token_obtain'),
                                     json.dumps(data),
                                     content_type='application/json')
        response2 = self.client.post(reverse('auth_token_obtain'),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertIn('access', response1.data)
        self.assertIn('refresh', response1.data)
        user = get_user_model().objects.get(username=user.get_username())
        self.assertIsNone(user.last_login)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response1.data['access'], response2.data['access'])
        self.assertEqual(OutstandingToken.objects.count(), 2)
        token1 = OutstandingToken.objects.get(token=response1.data['refresh'])
        self.assertEqual(token1.user, user)

    def test_token_update_last_login(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.last_login = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=1)
        user.save()
        last_login = user.last_login

        # WHEN
        data = {
            'username': user.get_username(),
            'password': 'test_pass_1!'
        }
        self.client.post(reverse('auth_token_obtain'),
                         json.dumps(data),
                         content_type='application/json')

        # THEN
        self.assertEqual(get_user_model().objects.get(pk=user.pk).last_login, last_login)

        # WHEN
        data = {
            'username': user.get_username(),
            'password': 'test_pass_1!',
            'last_login_now': True
        }
        self.client.post(reverse('auth_token_obtain'),
                         json.dumps(data),
                         content_type='application/json')

        # THEN
        self.assertNotEqual(get_user_model().objects.get(pk=user.pk).last_login, last_login)

    def test_delete_user_deletes_token(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'password': 'test_pass_1!'
        }
        response = self.client.delete(reverse('auth_user_resource_delete'), json.dumps(data),
                                      content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(OutstandingToken.objects.count(), 0)

    def test_token_fail_no_password(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        data = {
            'username': user.get_username(),
        }
        response = self.client.post(reverse('auth_token_obtain'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertEqual(OutstandingToken.objects.count(), 0)

    def test_token_with_email_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        data = {
            'username': user.email,
            'password': 'test_pass_1!'
        }
        response = self.client.post(reverse('auth_token_obtain'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_token_with_whitespace_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        data = {
            'username': f'  {user.email}  ',
            'password': 'test_pass_1!'
        }
        response = self.client.post(reverse('auth_token_obtain'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_refresh_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            "refresh": user.refresh
        }
        response = self.client.post(reverse('auth_token_refresh'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertNotEqual(response.data['access'], user.access)
        self.assertNotEqual(response.data['refresh'], user.refresh)
        self.assertEqual(OutstandingToken.objects.count(), 2)
        self.assertEqual(BlacklistedToken.objects.count(), 1)

    def test_blacklist_tokens_on_refresh(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        user3 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user3',
                                                                    email='test3@email.com')

        # THEN
        self.assertEqual(self.client.post(reverse('auth_token_refresh'),
                                          json.dumps({"refresh": user1.refresh}),
                                          content_type='application/json').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.post(reverse('auth_token_refresh'),
                                          json.dumps({"refresh": user2.refresh}),
                                          content_type='application/json').status_code, status.HTTP_200_OK)
        self.assertEqual(OutstandingToken.objects.count(), 5)
        self.assertEqual(BlacklistedToken.objects.count(), 2)
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user1.refresh).exists())
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user2.refresh).exists())
        self.assertFalse(BlacklistedToken.objects.filter(token__token=user3.refresh).exists())

        # THEN
        self.assertEqual(self.client.post(reverse('auth_token_refresh'),
                                          json.dumps({"refresh": user1.refresh}),
                                          content_type='application/json').status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse('auth_token_refresh'),
                                          json.dumps({"refresh": user2.refresh}),
                                          content_type='application/json').status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.post(reverse('auth_token_refresh'),
                                          json.dumps({"refresh": user3.refresh}),
                                          content_type='application/json').status_code, status.HTTP_200_OK)
        # Ensure all but the three current tokens are blacklisted
        self.assertEqual(OutstandingToken.objects.count(), 6)
        self.assertEqual(BlacklistedToken.objects.count(), 3)
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user1.refresh).exists())
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user2.refresh).exists())
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user3.refresh).exists())

    def test_blacklist_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(reverse('auth_token_blacklist'),
                                          json.dumps({"refresh": user.refresh}),
                                          content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OutstandingToken.objects.count(), 1)
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.assertTrue(BlacklistedToken.objects.filter(token__token=user.refresh).exists())

    def test_login_invalid_user(self):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.post(reverse('auth_token_obtain'),
                             json.dumps({'username': 'not-a-user', 'password': 'test_pass_1!'}),
                             content_type='application/json'),
            self.client.post(reverse('auth_token_obtain'),
                             json.dumps({'username': user.get_username(), 'password': 'wrong_pass'}),
                             content_type='application/json')
        ]

        # THEN
        for response in responses:
            self.assertContains(response, 'don\'t recognize that account',
                                status_code=status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(OutstandingToken.objects.count(), 0)

    def test_authenticated_view_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists(self.client)

        # WHEN
        response1 = self.client.get(reverse('auth_user_detail'))
        self.client.force_authenticate(user)
        response2 = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
