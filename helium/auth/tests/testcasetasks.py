import json
from datetime import datetime, timedelta

import pytz
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from helium.auth.tasks import expire_auth_tokens
from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.22'


class TestCaseTasks(APITestCase):
    def test_expire_auth_tokens(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        user3 = userhelper.given_a_user_exists(username='user3', email='test3@email.com')
        Token.objects.create(user=user1)
        token2 = Token.objects.create(user=user2)
        token2.created = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=29)
        token2.save()
        token3 = Token.objects.create(user=user3)
        token3.created = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=31)
        token3.save()
        self.assertEqual(Token.objects.count(), 3)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token3.key)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)

        # WHEN
        expire_auth_tokens()

        # THEN
        self.assertEqual(Token.objects.count(), 2)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_403_FORBIDDEN)
        self.client.credentials()

        # WHEN
        data = {
            'username': user3.email,
            'password': 'test_pass_1!'
        }
        response = self.client.post(reverse('auth_token_resource_obtain'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEquals(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Token.objects.count(), 3)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + response.data['token'])
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)
