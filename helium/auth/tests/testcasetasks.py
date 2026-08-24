from datetime import datetime, timedelta, timezone as dt_timezone

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
    sweep_dangling_users, purge_refresh_tokens, blacklist_refresh_token, emit_nightly_metrics,
    evaluate_review_prompts, delete_user, process_dormant_users, send_dormant_user_warning_email
)
from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, homeworkhelper


class TestCaseTasks(APITestCase):
    def test_purge_refresh_tokens(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        token1 = OutstandingToken.objects.get(token=user1.refresh)
        token1.expires_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
        token1.save()
        RefreshToken(token1.token).blacklist()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        token2 = OutstandingToken.objects.get(token=user2.refresh)
        token2.expires_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(seconds=1)
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

    def test_sweep_dangling_users(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user1.created_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user1.save()
        user2 = userhelper.given_an_inactive_user_exists(username='user2', email='test2@email.com')
        user2.created_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(
            days=settings.UNVERIFIED_USER_TTL_DAYS) + timedelta(minutes=1)
        user2.save()
        user3 = userhelper.given_an_inactive_user_exists(username='user3', email='test3@email.com')
        user3.created_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user3.save()
        user4 = userhelper.given_an_inactive_user_exists(username='user4', email='test4@email.com')
        user4.created_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS,
                                                                               minutes=1)
        user4.save()
        self.assertEqual(get_user_model().objects.count(), 4)

        # WHEN
        sweep_dangling_users()

        # THEN
        users = get_user_model().objects.all()
        self.assertEqual(len(users), 2)
        self.assertEqual(users[0].pk, user1.pk)
        self.assertEqual(users[1].pk, user2.pk)

    @mock.patch('helium.auth.tasks.taskutils.safe_apply_async')
    def test_sweep_dangling_users_requeues_stuck_pending_delete(self, mock_safe_apply_async):
        # GIVEN
        stuck = userhelper.given_a_user_exists(username='stuck', email='stuck@test.com')
        stuck.deletion_requested_at = timezone.now() - timedelta(minutes=30)
        stuck.save(update_fields=['deletion_requested_at'])

        fresh = userhelper.given_a_user_exists(username='fresh', email='fresh@test.com')
        fresh.deletion_requested_at = timezone.now() - timedelta(minutes=2)
        fresh.save(update_fields=['deletion_requested_at'])

        # WHEN
        sweep_dangling_users()

        # THEN
        queued_pks = [call.kwargs.get('args', [None])[0] for call in mock_safe_apply_async.call_args_list]
        self.assertIn(stuck.pk, queued_pks)
        self.assertNotIn(fresh.pk, queued_pks)

        # AND: users not deleted by sweep itself — deletion runs asynchronously via the queued task
        self.assertTrue(get_user_model().objects.filter(pk=stuck.pk).exists())
        self.assertTrue(get_user_model().objects.filter(pk=fresh.pk).exists())

    @mock.patch('helium.auth.tasks.taskutils.safe_apply_async')
    def test_sweep_dangling_users_does_not_requeue_in_flight_pending_delete(self, mock_safe_apply_async):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.deletion_requested_at = timezone.now() - timedelta(minutes=2)
        user.save(update_fields=['deletion_requested_at'])

        # WHEN
        sweep_dangling_users()

        # THEN
        queued_pks = [call.kwargs.get('args', [None])[0] for call in mock_safe_apply_async.call_args_list]
        self.assertNotIn(user.pk, queued_pks)

    def test_verification_email_url_encodes_special_characters(self):
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

        # WHEN/THEN
        blacklist_refresh_token(user.refresh)

    def test_delete_user_not_found(self):
        # GIVEN

        # WHEN/THEN
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

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_emits_class_schedules_adoption(self, mock_gauge):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        adoption_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.class_schedules.pct']
        self.assertTrue(adoption_calls)
        self.assertTrue(any(c.args[1] == 100 for c in adoption_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_excludes_weekly_schedules_from_rotating_adoption(self, mock_gauge):
        # GIVEN a user whose only schedule is an ordinary weekly one
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN - counts as a class-schedule adopter but not a rotating-schedule adopter
        class_calls = [c for c in mock_gauge.call_args_list
                       if c.args[0] == 'users.adoption.class_schedules.pct']
        rotating_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.rotating_schedules.pct']
        self.assertTrue(any(c.args[1] == 100 for c in class_calls))
        self.assertTrue(rotating_calls)
        self.assertTrue(all(c.args[1] == 0 for c in rotating_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_emits_rotating_schedules_adoption(self, mock_gauge):
        # GIVEN a user with a cycle schedule
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_cycle_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        rotating_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.rotating_schedules.pct']
        self.assertTrue(rotating_calls)
        self.assertTrue(any(c.args[1] == 100 for c in rotating_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_counts_week_based_schedules_as_rotating_adoption(self, mock_gauge):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_week_based_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        rotating_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.rotating_schedules.pct']
        self.assertTrue(rotating_calls)
        self.assertTrue(any(c.args[1] == 100 for c in rotating_calls))

    @mock.patch('helium.auth.tasks.metricutils.distribution')
    def test_emit_nightly_metrics_partitions_schedules_per_user_by_type(self, mock_distribution):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)
        courseschedulehelper.given_cycle_schedule_exists(course)
        courseschedulehelper.given_week_based_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        def samples(entity=None):
            tag = f'entity:{entity}' if entity else None
            return [c.args[1] for c in mock_distribution.call_args_list
                    if c.args[0] == 'users.data.schedules_per_user'
                    and (tag in c.kwargs['extra_tags'] if tag
                         else not any(t.startswith('entity:') for t in c.kwargs['extra_tags']))]

        self.assertTrue(all(v == 3 for v in samples()))
        for entity in ('weekly', 'cycle', 'week_based'):
            self.assertTrue(samples(entity), f'no samples for {entity}')
            self.assertTrue(all(v == 1 for v in samples(entity)), entity)

        # THEN the breakdowns sum to the total
        self.assertEqual(sum(samples(e)[0] for e in ('weekly', 'cycle', 'week_based')),
                         samples()[0])

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_measures_rotating_adoption_against_scheduled_users(self, mock_gauge):
        # GIVEN
        scheduled_user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(scheduled_user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_cycle_schedule_exists(course)
        userhelper.given_a_user_exists(username='no_schedule', email='no_schedule@test.com')

        # WHEN
        emit_nightly_metrics()

        # THEN
        of_all_calls = [c for c in mock_gauge.call_args_list
                        if c.args[0] == 'users.adoption.rotating_schedules.pct']
        of_scheduled_calls = [c for c in mock_gauge.call_args_list
                              if c.args[0] == 'users.adoption.rotating_schedules.of_scheduled.pct']
        self.assertTrue(any(c.args[1] == 50 for c in of_all_calls))
        self.assertTrue(of_scheduled_calls)
        self.assertTrue(all(c.args[1] == 100 for c in of_scheduled_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_excludes_schedules_that_meet_no_days_from_class_schedules_adoption(self, mock_gauge):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0000000')

        # WHEN
        emit_nightly_metrics()

        # THEN
        adoption_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.class_schedules.pct']
        self.assertTrue(adoption_calls)
        self.assertTrue(all(c.args[1] == 0 for c in adoption_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_counts_cycle_schedules_with_no_weekdays_as_class_schedules_adoption(self, mock_gauge):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_cycle_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        self.assertEqual(schedule.days_of_week, '0000000')
        adoption_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.class_schedules.pct']
        self.assertTrue(adoption_calls)
        self.assertTrue(any(c.args[1] == 100 for c in adoption_calls))

    @mock.patch('helium.auth.tasks.metricutils.gauge')
    def test_emit_nightly_metrics_excludes_example_schedule_from_class_schedules_adoption(self, mock_gauge):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course_group.example_schedule = True
        course_group.save()
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        emit_nightly_metrics()

        # THEN
        adoption_calls = [c for c in mock_gauge.call_args_list
                          if c.args[0] == 'users.adoption.class_schedules.pct']
        self.assertTrue(adoption_calls)
        self.assertTrue(all(c.args[1] == 0 for c in adoption_calls))

    @mock.patch('helium.auth.tasks.send_dormant_user_warning_email.apply_async')
    @mock.patch('helium.auth.tasks.delete_user.apply_async')
    def test_process_dormant_users_sends_first_warning(self, mock_delete, mock_send_warning):
        # GIVEN
        user = userhelper.given_a_user_exists()
        dormant_date = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=settings.DORMANT_USER_THRESHOLD_YEARS * 365 + 1)
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
        dormant_date = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=settings.DORMANT_USER_THRESHOLD_YEARS * 365 + 31)
        user.last_activity = dormant_date
        user.deletion_warning_count = 4
        user.deletion_warning_sent_at = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=2)
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
        recent_date = datetime.now().replace(tzinfo=dt_timezone.utc) - timedelta(days=30)
        user.last_activity = recent_date
        user.save()

        # WHEN
        process_dormant_users()

        # THEN
        mock_send_warning.assert_not_called()
        mock_delete.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)
