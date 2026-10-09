from unittest import mock

from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common.models import MetricSample
from helium.common.services import cumulativeuserservice
from helium.common.tests.helpers import metricsamplehelper


@mock.patch('helium.common.services.metricsampleservice.metricutils.gauge')
class TestCaseCumulativeUserService(TestCase):
    def setUp(self):
        metricsamplehelper.given_total_users_seed(0)

    def test_milestones_and_tourists(self, mock_gauge):
        # GIVEN
        metricsamplehelper.given_a_user_with_tenure('stayed', 'stayed@test.com', 100, 95)
        metricsamplehelper.given_a_user_with_tenure('month', 'month@test.com', 40, 35)
        metricsamplehelper.given_a_user_with_tenure('tourist', 'tourist@test.com', 20, 3)
        metricsamplehelper.given_a_user_with_tenure('new', 'new@test.com', 3, 1)
        metricsamplehelper.given_a_user_with_tenure('staff', 'staff@heliumedu.com', 100, 95)
        userhelper.given_an_inactive_user_exists(username='pending', email='pending@test.com')

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        metricsamplehelper.verify_cumulative_users(self, mock_gauge, {
            'total': 4, 'verified': 4, 'tourists': 1, '7d': 2, '30d': 2, '90d': 1,
        })

    def test_total_is_seed_plus_verified_non_staff_users_created_since(self, mock_gauge):
        # GIVEN
        seeded = userhelper.given_an_inactive_user_exists(username='seeded', email='seeded@test.com')
        metricsamplehelper.given_total_users_seed(seeded.pk)
        seeded.is_active = True
        seeded.save()
        userhelper.given_a_user_exists(username='new', email='new@test.com')
        userhelper.given_a_user_exists(username='staff', email='staff@heliumedu.com')
        userhelper.given_an_inactive_user_exists(username='pending', email='pending@test.com')
        gone = userhelper.given_a_user_exists(username='gone', email='gone@test.com')
        cumulativeuserservice.record_deleted_user(gone)
        gone.delete()

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        self.assertEqual(MetricSample.objects.get(metric='users.cumulative', dimension='milestone:total').value,
                         seeded.pk + 2)

    def test_deleted_users_stay_counted_and_staff_are_not_tallied(self, mock_gauge):
        # GIVEN
        real = metricsamplehelper.given_a_user_with_tenure('real', 'real@test.com', 40, 35)
        staff = metricsamplehelper.given_a_user_with_tenure('staff', 'staff@heliumedu.com', 40, 35)
        for user in (real, staff):
            cumulativeuserservice.record_deleted_user(user)
            user.delete()

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        metricsamplehelper.verify_cumulative_users(self, mock_gauge, {
            'total': 1, 'verified': 1, 'tourists': 0, '7d': 1, '30d': 1, '90d': 0,
        })
        self.assertEqual(list(MetricSample.objects.filter(metric='users.deleted').values_list('dimension', 'value')),
                         [('span_days:35', 1)])

    def test_deleted_unverified_user_not_tallied(self, mock_gauge):
        # GIVEN
        pending = userhelper.given_an_inactive_user_exists(username='pending', email='pending@test.com')
        cumulativeuserservice.record_deleted_user(pending)
        pending.delete()

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        metricsamplehelper.verify_cumulative_users(self, mock_gauge, {
            'total': 0, 'verified': 0, 'tourists': 0, '7d': 0, '30d': 0, '90d': 0,
        })
        self.assertFalse(MetricSample.objects.filter(metric='users.deleted').exists())

    def test_rerun_same_day_is_idempotent(self, mock_gauge):
        # GIVEN
        metricsamplehelper.given_a_user_with_tenure('month', 'month@test.com', 40, 35)
        cumulativeuserservice.record_cumulative_users()

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        self.assertEqual(MetricSample.objects.filter(metric='users.cumulative').count(), 6)
        self.assertEqual(MetricSample.objects.get(metric='users.cumulative', dimension='milestone:30d').value, 1)

    def test_milestones_independent_of_user_time_zone(self, mock_gauge):
        # GIVEN
        now = timezone.now()
        metricsamplehelper.given_a_user_with_tenure('east', 'east@test.com', 40, 30, time_zone='Pacific/Auckland',
                                                    now=now)
        metricsamplehelper.given_a_user_with_tenure('west', 'west@test.com', 40, 30, time_zone='America/Los_Angeles',
                                                    now=now)

        # WHEN
        cumulativeuserservice.record_cumulative_users()

        # THEN
        metricsamplehelper.verify_cumulative_users(self, mock_gauge, {
            'total': 2, 'verified': 2, 'tourists': 0, '7d': 2, '30d': 2, '90d': 0,
        })
