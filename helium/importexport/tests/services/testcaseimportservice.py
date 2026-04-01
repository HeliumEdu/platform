__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest.mock import patch

import pytz
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.importexport.services.importservice import import_example_schedule
from helium.planner.models import CourseGroup


class TestCaseAdjustScheduleRelativeTo(TestCase):
    """
    Tests for _adjust_schedule_relative_to, exercised via import_example_schedule.

    The key regression: timezone.now() always returns UTC, so a user whose local date
    is still in month N (because they're UTC-N hours) would incorrectly have their
    schedule anchored to month N+1's previous month rather than month N's previous month.
    This manifests at CI runs that cross UTC midnight at a month boundary.
    """

    def _create_user_with_timezone(self, tz_name):
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = tz_name
        user.settings.save()
        return user

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_uses_user_timezone_when_behind_utc_at_month_boundary(self, mock_now):
        # GIVEN: UTC has crossed into April 1, but America/New_York (EDT, UTC-4) is still March 31
        mock_now.return_value = datetime.datetime(2026, 4, 1, 0, 30, 0, tzinfo=pytz.UTC)
        user = self._create_user_with_timezone('America/New_York')

        # WHEN
        import_example_schedule(user)

        # THEN: anchor should use user's local month (March), so previous month = February
        # First Monday of February 2026 = February 2
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 2, 2),
        )

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_uses_utc_month_when_user_timezone_is_utc(self, mock_now):
        # GIVEN: UTC has crossed into April 1; UTC user is also in April
        mock_now.return_value = datetime.datetime(2026, 4, 1, 0, 30, 0, tzinfo=pytz.UTC)
        user = self._create_user_with_timezone('UTC')

        # WHEN
        import_example_schedule(user)

        # THEN: anchor should use user's local month (April), so previous month = March
        # First Monday of March 2026 = March 2
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 3, 2),
        )

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_day_before_utc_month_boundary(self, mock_now):
        # GIVEN: UTC is still March 31; both UTC and America/New_York agree on March
        mock_now.return_value = datetime.datetime(2026, 3, 31, 23, 30, 0, tzinfo=pytz.UTC)
        user = self._create_user_with_timezone('America/New_York')

        # WHEN
        import_example_schedule(user)

        # THEN: both timezones are in March, so previous month = February
        # First Monday of February 2026 = February 2
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 2, 2),
        )
