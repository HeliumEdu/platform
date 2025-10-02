__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.2"

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.models.userpushtoken import UserPushToken
from helium.auth.tests.helpers import userhelper


class TestCasePushTokenViews(APITestCase):
    def test_push_token_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('auth_user_pushtoken_list')),
            self.client.post(reverse('auth_user_pushtoken_list')),
            self.client.get(reverse('auth_user_pushtoken_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('auth_user_pushtoken_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_push_tokens(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        userhelper.given_user_push_token_exists(user1)
        userhelper.given_user_push_token_exists(user2, token='token2', device_id='device2')
        userhelper.given_user_push_token_exists(user2, token='token3', device_id='device3')

        # WHEN
        response1 = self.client.get(reverse('auth_user_pushtoken_list'))
        response2 = self.client.get(reverse('auth_user_pushtoken_list') + f'?device_id=device2')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(UserPushToken.objects.count(), 3)
        self.assertEqual(len(response1.data), 2)
        self.assertEqual(len(response2.data), 1)

    def test_create_push_token(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'device_id': 'device1',
            'token': 'token1',
            'user': user.pk
        }
        response = self.client.post(reverse('auth_user_pushtoken_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserPushToken.objects.count(), 1)
        push_token = UserPushToken.objects.get(pk=response.data['id'])
        userhelper.verify_push_token_matches(self, push_token, response.data)

    def test_get_push_token_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        push_token = userhelper.given_user_push_token_exists(user)

        # WHEN
        response = self.client.get(reverse('auth_user_pushtoken_detail',
                                           kwargs={'pk': push_token.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        userhelper.verify_push_token_matches(self, push_token, response.data)

    def test_delete_push_token_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        push_token = userhelper.given_user_push_token_exists(user)

        # WHEN
        response = self.client.delete(reverse('auth_user_pushtoken_detail',
                                              kwargs={'pk': push_token.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(UserPushToken.objects.filter(pk=push_token.pk).exists())
        self.assertEqual(UserPushToken.objects.count(), 0)
