__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.32"

import json
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from helium.auth.tasks import purge_expired_tokens, purge_unverified_users
from helium.auth.tests.helpers import userhelper


class TestCaseTasks(APITestCase):
    def test_purge_expired_auth_tokens(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user3',
                                                            email='test3@email.com')
        token2 = OutstandingToken.objects.get(user=user2)
        token2.expires_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(seconds=1)
        token2.save()

        # THEN
        self.assertEqual(OutstandingToken.objects.count(), 3)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + user1.access)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token2.token)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_403_FORBIDDEN)

        # WHEN
        purge_expired_tokens()

        # THEN
        self.assertEqual(OutstandingToken.objects.count(), 2)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + user1.access)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token2.token)
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_403_FORBIDDEN)
        self.client.credentials()

        # WHEN
        data = {
            'username': user2.email,
            'password': 'test_pass_1!'
        }
        response = self.client.post(reverse('auth_token_obtain'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(OutstandingToken.objects.count(), 3)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        self.assertEqual(self.client.get(reverse('auth_user_detail')).status_code, status.HTTP_200_OK)

    def test_purge_unverified_users(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user1.created_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user1.save()
        user2 = userhelper.given_an_inactive_user_exists(username='user2', email='test2@email.com')
        user2.created_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(
            days=settings.UNVERIFIED_USER_TTL_DAYS) + timedelta(minutes=1)
        user2.save()
        user3 = userhelper.given_an_inactive_user_exists(username='user3', email='test3@email.com')
        user3.created_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user3.save()
        user4 = userhelper.given_an_inactive_user_exists(username='user4', email='test4@email.com')
        user4.created_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user4.save()
        self.assertEqual(get_user_model().objects.count(), 4)

        # WHEN
        purge_unverified_users()

        # THEN
        users = get_user_model().objects.all()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0].pk, user1.pk)
        self.assertEqual(users[1].pk, user2.pk)
