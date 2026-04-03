__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.template.loader import get_template
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from unittest import mock

from helium.auth.tasks import (
    purge_unverified_users, purge_refresh_tokens, blacklist_refresh_token, user_watchdog, delete_user,
    process_dormant_users, send_dormant_user_warning_email
)
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

    def test_verification_email_url_encodes_special_characters(self):
        """Test that verification email properly URL-encodes email addresses with special characters like +."""
        # GIVEN
        email_with_plus = 'contact+test@example.com'
        context = {
            'PROJECT_NAME': 'Helium',
            'email': email_with_plus,
            'verification_code': 123456,
            'verify_url': 'https://app.heliumedu.com/verify',
        }

        # WHEN
        html_template = get_template('email/verification.html')
        html_content = html_template.render(context)
        txt_template = get_template('email/verification.txt')
        txt_content = txt_template.render(context)

        # THEN
        # The + should be encoded as %2B in the URL, not left as + (which would be decoded as space)
        expected_encoded_email = 'contact%2Btest%40example.com'
        self.assertIn(expected_encoded_email, html_content)
        self.assertIn(expected_encoded_email, txt_content)
        # Make sure the raw + is NOT in the URL portion (it should only appear in the display text)
        self.assertNotIn(f'?email={email_with_plus}', html_content)
        self.assertNotIn(f'?email={email_with_plus}', txt_content)

    def test_blacklist_refresh_token_already_blacklisted(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        RefreshToken(user.refresh).blacklist()

        # WHEN/THEN - should not raise, just log and continue
        blacklist_refresh_token(user.refresh)

    def test_delete_user_not_found(self):
        # GIVEN - user ID that doesn't exist

        # WHEN/THEN - should not raise, just log and continue
        delete_user(99999)

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_user_watchdog(self, mock_gauge):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        user_watchdog()

        # THEN
        self.assertEqual(mock_gauge.call_count, 10)  # 5 time windows for staff/non-staff

    @override_settings(DORMANT_USER_PURGE_MAX_PER_RUN=1)
    @mock.patch('helium.auth.tasks.send_dormant_user_warning_email.apply_async')
    @mock.patch('helium.auth.tasks.delete_user.apply_async')
    def test_process_dormant_users_sends_first_warning(self, mock_delete, mock_send_warning):
        # GIVEN
        user = userhelper.given_a_user_exists()
        dormant_date = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.DORMANT_USER_THRESHOLD_YEARS * 365 + 1)
        user.last_activity = dormant_date
        user.deletion_warning_count = 0
        user.save()

        # WHEN
        process_dormant_users()

        # THEN
        mock_send_warning.assert_called_once()
        self.assertEqual(mock_send_warning.call_args[1]['args'], (user.pk,))
        mock_delete.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)

    @override_settings(DORMANT_USER_PURGE_MAX_PER_RUN=1)
    @mock.patch('helium.auth.tasks.send_dormant_user_warning_email.apply_async')
    def test_process_dormant_users_deletes_after_all_warnings(self, mock_send_warning):
        # GIVEN
        user = userhelper.given_a_user_exists()
        dormant_date = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.DORMANT_USER_THRESHOLD_YEARS * 365 + 31)
        user.last_activity = dormant_date
        user.deletion_warning_count = 4
        user.deletion_warning_sent_at = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=2)
        user.save()
        self.assertEqual(get_user_model().objects.count(), 1)

        # WHEN
        process_dormant_users()

        # THEN
        mock_send_warning.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 0)

    @override_settings(DORMANT_USER_PURGE_MAX_PER_RUN=1)
    @mock.patch('helium.auth.tasks.send_dormant_user_warning_email.apply_async')
    @mock.patch('helium.auth.tasks.delete_user.apply_async')
    def test_process_dormant_users_ignores_active_users(self, mock_delete, mock_send_warning):
        # GIVEN
        user = userhelper.given_a_user_exists()
        recent_date = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=30)
        user.last_activity = recent_date
        user.save()

        # WHEN
        process_dormant_users()

        # THEN
        mock_send_warning.assert_not_called()
        mock_delete.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)
