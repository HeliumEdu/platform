__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.urls import reverse
from knox.models import AuthToken
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase


class TestCaseApiTokenViews(APITestCase, CacheTestCase):
    def test_create_returns_plaintext_token_and_authenticates(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        create_response = self.client.post(reverse('auth_api_token'))

        # THEN
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', create_response.data)
        self.assertIn('created_at', create_response.data)
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 1)

        # AND: the plaintext authenticates a protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {create_response.data["token"]}')
        protected_response = self.client.get(reverse('auth_user_detail'))
        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)
        self.assertEqual(protected_response.data['email'], user.email)

    def test_only_hash_persisted(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        create_response = self.client.post(reverse('auth_api_token'))

        # THEN
        plaintext = create_response.data['token']
        instance = AuthToken.objects.get(user=user)
        self.assertNotEqual(instance.digest, plaintext)
        self.assertGreater(len(instance.digest), len(plaintext))

    def test_create_rotates_existing_token(self):
        # GIVEN: a user with an existing API token
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        first_response = self.client.post(reverse('auth_api_token'))
        first_token = first_response.data['token']

        # WHEN: a second create call is made
        second_response = self.client.post(reverse('auth_api_token'))

        # THEN: a new token is issued and only the latest is valid
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        second_token = second_response.data['token']
        self.assertNotEqual(first_token, second_token)
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 1)

        # AND: the prior token no longer authenticates
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {first_token}')
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code,
                         status.HTTP_401_UNAUTHORIZED)

        # AND: the new token does
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {second_token}')
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code,
                         status.HTTP_200_OK)

    def test_delete_revokes_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        create_response = self.client.post(reverse('auth_api_token'))
        token = create_response.data['token']

        # WHEN
        delete_response = self.client.delete(reverse('auth_api_token'))

        # THEN
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 0)

        # AND: the revoked token no longer authenticates
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code,
                         status.HTTP_401_UNAUTHORIZED)

    def test_delete_is_idempotent_when_no_token_exists(self):
        # GIVEN: an authenticated user with no API token
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        delete_response = self.client.delete(reverse('auth_api_token'))

        # THEN
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_password_change_does_not_invalidate_api_token(self):
        # GIVEN: a user with an API token
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        create_response = self.client.post(reverse('auth_api_token'))
        token = create_response.data['token']

        # WHEN: the user's password changes
        user.set_password('new_pass_2!')
        user.save()

        # THEN: the API token still authenticates
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        protected_response = self.client.get(reverse('auth_user_detail'))
        self.assertEqual(protected_response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_create_or_revoke(self):
        # GIVEN: no credentials on the client

        # WHEN / THEN
        self.assertEqual(self.client.post(reverse('auth_api_token')).status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(reverse('auth_api_token')).status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(AuthToken.objects.count(), 0)

    def test_api_token_cannot_manage_itself(self):
        # GIVEN: a user with an API token, credentials switched to that token
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        create_response = self.client.post(reverse('auth_api_token'))
        token = create_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # WHEN / THEN: POST and DELETE both fail
        self.assertEqual(self.client.post(reverse('auth_api_token')).status_code,
                         status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.client.delete(reverse('auth_api_token')).status_code,
                         status.HTTP_401_UNAUTHORIZED)

        # AND: the original token is untouched
        self.assertEqual(AuthToken.objects.filter(user=user).count(), 1)
