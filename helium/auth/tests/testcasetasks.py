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

from django.utils import timezone

from helium.auth.tasks import (
    purge_unverified_users, purge_refresh_tokens, blacklist_refresh_token, emit_nightly_metrics,
    evaluate_review_prompts, delete_user, process_dormant_users, send_dormant_user_warning_email
)
from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper


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
    def test_emit_nightly_metrics_emits_active_user_metrics(self, mock_gauge):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        emit_nightly_metrics()

        # THEN
        active_user_calls = [c for c in mock_gauge.call_args_list if c.args[0] == 'users.active']
        self.assertEqual(len(active_user_calls), 10)  # 5 time windows × staff/non-staff

    def _setup_review_prompt_candidate(self, username='test_user', email='user@test.com'):
        user = userhelper.given_a_user_exists(username=username, email=email)
        user.settings.next_review_prompt_date = timezone.now() - timedelta(days=1)
        user.settings.save(update_fields=['next_review_prompt_date'])
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        return user, course

    def test_evaluate_review_prompts_flags_user_with_sufficient_total_and_recent_completions(self):
        # GIVEN: 7 total completed, 4 of them within the last 7 days
        user, course = self._setup_review_prompt_candidate()
        recent_date = timezone.now() - timedelta(days=3)
        old_date = timezone.now() - timedelta(days=30)
        for _ in range(4):
            hw = homeworkhelper.given_homework_exists(course, completed=True)
            hw.completed_at = recent_date
            hw.save(update_fields=['completed_at'])
        for _ in range(3):
            hw = homeworkhelper.given_homework_exists(course, completed=True)
            hw.completed_at = old_date
            hw.save(update_fields=['completed_at'])

        # WHEN
        evaluate_review_prompts()

        # THEN
        user.settings.refresh_from_db()
        self.assertTrue(user.settings.prompt_for_review)

    def test_evaluate_review_prompts_does_not_flag_user_with_insufficient_recent_completions(self):
        # GIVEN: 7 total completed but only 3 within the last 7 days
        user, course = self._setup_review_prompt_candidate()
        recent_date = timezone.now() - timedelta(days=3)
        old_date = timezone.now() - timedelta(days=30)
        for _ in range(3):
            hw = homeworkhelper.given_homework_exists(course, completed=True)
            hw.completed_at = recent_date
            hw.save(update_fields=['completed_at'])
        for _ in range(4):
            hw = homeworkhelper.given_homework_exists(course, completed=True)
            hw.completed_at = old_date
            hw.save(update_fields=['completed_at'])

        # WHEN
        evaluate_review_prompts()

        # THEN
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.prompt_for_review)

    def test_evaluate_review_prompts_excludes_example_schedule_homework(self):
        # GIVEN: enough completions to trigger, but all from an example schedule course group
        user, _ = self._setup_review_prompt_candidate()
        example_course_group = coursegrouphelper.given_course_group_exists(user, title='Example')
        example_course_group.example_schedule = True
        example_course_group.save(update_fields=['example_schedule'])
        example_course = coursehelper.given_course_exists(example_course_group)
        recent_date = timezone.now() - timedelta(days=3)
        for _ in range(7):
            hw = homeworkhelper.given_homework_exists(example_course, completed=True)
            hw.completed_at = recent_date
            hw.save(update_fields=['completed_at'])

        # WHEN
        evaluate_review_prompts()

        # THEN: not flagged because all completed homework is from the example schedule
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.prompt_for_review)

    @override_settings(REVIEW_PROMPT_MAX_SHOWN=1)
    def test_evaluate_review_prompts_does_not_flag_user_at_max_prompts_shown(self):
        # GIVEN: eligible by homework count but already at max prompts shown
        user, course = self._setup_review_prompt_candidate()
        user.settings.review_prompts_shown = 1
        user.settings.save(update_fields=['review_prompts_shown'])
        recent_date = timezone.now() - timedelta(days=3)
        for _ in range(7):
            hw = homeworkhelper.given_homework_exists(course, completed=True)
            hw.completed_at = recent_date
            hw.save(update_fields=['completed_at'])

        # WHEN
        evaluate_review_prompts()

        # THEN
        user.settings.refresh_from_db()
        self.assertFalse(user.settings.prompt_for_review)

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
