__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.10"

from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.tasks import purge_unverified_users, purge_refresh_tokens
from helium.auth.tests.helpers import userhelper


class TestCaseTasks(APITestCase):
    def test_purge_refresh_tokens(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        token1 = OutstandingToken.objects.get(token=user1.refresh)
        token1.expires_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(seconds=1)
        token1.save()
        RefreshToken(token1.token).blacklist()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        token2 = OutstandingToken.objects.get(token=user2.refresh)
        token2.expires_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(seconds=1)
        token2.save()
        RefreshToken(token2.token).blacklist()
        user3 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user3',
                                                                    email='test3@email.com')
        self.assertEqual(OutstandingToken.objects.count(), 3)
        self.assertEqual(BlacklistedToken.objects.count(), 2)

        # WHEN
        purge_refresh_tokens()

        # THEN
        self.assertEqual(OutstandingToken.objects.count(), 1)
        self.assertEqual(BlacklistedToken.objects.count(), 0)
        self.assertTrue(OutstandingToken.objects.filter(token=user3.refresh).exists())

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
