__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.importexport.services.importservice import _adjust_schedule_relative_to
from helium.importexport.tasks import import_example_schedule
from helium.planner.models import Event, Homework
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper


class TestCaseImportExportTasks(APITestCase):
    def test_import_example_schedule_sets_is_setup_complete(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        self.assertFalse(user.settings.is_setup_complete)

        # WHEN
        import_example_schedule(user.pk)

        # THEN
        user.refresh_from_db()
        self.assertTrue(user.settings.is_setup_complete)

    def test_import_example_schedule_nonexistent_user_does_not_fail(self):
        # GIVEN
        nonexistent_user_id = 99999

        # WHEN / THEN (should not raise)
        import_example_schedule(nonexistent_user_id)

    def test_adjust_schedule_preserves_local_wall_clock_time_across_dst(self):
        """
        _adjust_schedule_relative_to must preserve the user's local wall-clock
        time when shifting example-schedule dates across a DST boundary.

        Scenario: items stored at 17:00 UTC (= 11 AM CST, UTC-6) are adjusted
        so that one lands on 2026-03-02 (pre-DST, still CST) and one lands on
        2026-03-09 (post-DST, CDT = UTC-5). The post-DST item must be stored as
        16:00 UTC (11 AM CDT) not 17:00 UTC (which would display as 12 PM CDT).
        """
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()

        # Course group and course whose start_date aligns with first_monday in
        # the source file (2026-02-02 = the Monday we'll compute deltas from).
        course_group = coursegrouphelper.given_course_group_exists(
            user,
            start_date=datetime.date(2026, 2, 2),
            end_date=datetime.date(2026, 4, 4),
        )
        course_group.example_schedule = True
        course_group.save()

        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 2, 2),
            end_date=datetime.date(2026, 4, 4),
        )

        # Two homework items stored at 17:00 UTC (= 11 AM CST).
        # hw_pre_dst is on 2026-02-02 → delta=0  → will land on 2026-03-02 (CST)
        # hw_post_dst is on 2026-02-09 → delta=7 → will land on 2026-03-09 (CDT)
        hw_pre_dst = homeworkhelper.given_homework_exists(
            course,
            start=datetime.datetime(2026, 2, 2, 17, 0, 0, tzinfo=timezone.utc),
            end=datetime.datetime(2026, 2, 2, 17, 30, 0, tzinfo=timezone.utc),
        )
        hw_post_dst = homeworkhelper.given_homework_exists(
            course,
            start=datetime.datetime(2026, 2, 9, 17, 0, 0, tzinfo=timezone.utc),
            end=datetime.datetime(2026, 2, 9, 17, 30, 0, tzinfo=timezone.utc),
        )

        # A single example-schedule Event is required by _adjust_schedule_relative_to
        # to compute the events_delta; give it a start time of 17:00 UTC as well.
        Event.objects.create(
            title='Test Event',
            all_day=False,
            show_end_time=False,
            start=datetime.datetime(2026, 2, 9, 17, 0, 0, tzinfo=timezone.utc),
            end=datetime.datetime(2026, 2, 9, 17, 30, 0, tzinfo=timezone.utc),
            priority=50,
            example_schedule=True,
            user=user,
        )

        # Mock now() to 2026-04-06 12:00 UTC.
        # adjust_month=-1  →  adjusted_month = March 2026
        # March 1, 2026 is a Sunday (weekday=6), so first_monday = March 2, 2026.
        mock_now = datetime.datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc)

        # WHEN
        with patch('django.utils.timezone.now', return_value=mock_now):
            _adjust_schedule_relative_to(user, -1)

        # THEN
        hw_pre_dst.refresh_from_db()
        hw_post_dst.refresh_from_db()

        # 2026-03-02 is pre-DST (CST = UTC-6): 11 AM local = 17:00 UTC
        self.assertEqual(
            hw_pre_dst.start,
            datetime.datetime(2026, 3, 2, 17, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            hw_pre_dst.end,
            datetime.datetime(2026, 3, 2, 17, 30, 0, tzinfo=timezone.utc),
        )

        # 2026-03-09 is post-DST (CDT = UTC-5): 11 AM local = 16:00 UTC (NOT 17:00)
        self.assertEqual(
            hw_post_dst.start,
            datetime.datetime(2026, 3, 9, 16, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(
            hw_post_dst.end,
            datetime.datetime(2026, 3, 9, 16, 30, 0, tzinfo=timezone.utc),
        )
