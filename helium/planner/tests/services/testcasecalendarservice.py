__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.services import calendarservice
from helium.planner.tests.helpers import (coursegrouphelper, coursehelper, eventhelper,
                                          homeworkhelper, reminderhelper)


def _midnight_in_tz_as_utc(date, tz_name):
    naive = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
    return naive.replace(tzinfo=ZoneInfo(tz_name)).astimezone(datetime.timezone.utc)


class TestCaseCalendarService(TestCase):
    """
    GIVEN/WHEN/THEN tests for the timezone-change normalization service.

    The bug being prevented: all-day events are stored as UTC datetimes representing
    midnight in the user's local timezone. After a timezone change, those UTC values
    no longer align with midnight in the new tz, causing the calendar to render the
    event as spanning two adjacent days. The service rebases `start`/`end` so the
    user's local date observation is preserved.
    """

    def test_single_day_all_day_event_chicago_to_la_preserves_local_date(self):
        # GIVEN
        # All-day event "Project 2" on Friday May 8 2026 in Chicago — stored as midnight CDT
        # (which is 05:00 UTC since CDT = UTC-5 in May).
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            title='Project 2',
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Los_Angeles'
        )

        # THEN
        event.refresh_from_db()
        # start/end now represent midnight in LA on the same local dates the user was seeing
        self.assertEqual(
            event.start, _midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Los_Angeles')
        )
        self.assertEqual(
            event.end, _midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Los_Angeles')
        )
        # And critically, the local date the user observes in LA is still May 8
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2026, 5, 8))

    def test_la_to_chicago_inverse_direction(self):
        # GIVEN — mirrored bug case (the screenshot showing Project 2 spanning Fri+Sat)
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Los_Angeles'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Los_Angeles'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Los_Angeles'),
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Los_Angeles', 'America/Chicago'
        )

        # THEN
        event.refresh_from_db()
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Chicago')).date(),
                         datetime.date(2026, 5, 8))
        self.assertEqual(event.end.astimezone(ZoneInfo('America/Chicago')).date(),
                         datetime.date(2026, 5, 9))

    def test_multi_day_all_day_event_preserves_both_endpoints(self):
        # GIVEN — "Parents Weekend" Oct 31 → Nov 3 in Chicago
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            title='Parents Weekend',
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2025, 10, 31), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2025, 11, 3), 'America/Chicago'),
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Los_Angeles'
        )

        # THEN
        event.refresh_from_db()
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2025, 10, 31))
        self.assertEqual(event.end.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2025, 11, 3))

    def test_non_all_day_event_is_left_alone(self):
        # GIVEN — a 1pm meeting in Chicago should remain at the same UTC instant after tz change
        # (semantically: "same physical moment, displayed in your new local clock")
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        original_start = datetime.datetime(2026, 5, 8, 18, 0, 0, tzinfo=datetime.timezone.utc)
        original_end = datetime.datetime(2026, 5, 8, 19, 0, 0, tzinfo=datetime.timezone.utc)
        event = eventhelper.given_event_exists(
            user, all_day=False, start=original_start, end=original_end,
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Los_Angeles'
        )

        # THEN
        event.refresh_from_db()
        self.assertEqual(event.start, original_start)
        self.assertEqual(event.end, original_end)

    def test_homework_all_day_is_normalized(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(
            course,
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Los_Angeles'
        )

        # THEN
        homework.refresh_from_db()
        self.assertEqual(homework.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2026, 5, 8))

    def test_no_op_when_timezone_unchanged(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        original_start = _midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago')
        event = eventhelper.given_event_exists(
            user, all_day=True,
            start=original_start,
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Chicago'
        )

        # THEN
        event.refresh_from_db()
        self.assertEqual(event.start, original_start)

    @mock.patch('helium.planner.services.calendarservice.taskutils.safe_apply_async')
    def test_reminders_are_queued_for_recomputation(self, mock_safe_apply_async):
        # GIVEN — an all-day event with a reminder attached
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user, all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )
        reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        calendarservice.normalize_all_day_for_timezone_change(
            user, 'America/Chicago', 'America/Los_Angeles'
        )

        # THEN — adjust_reminder_times is queued for the affected event
        queued_calls = [c for c in mock_safe_apply_async.call_args_list
                        if c.kwargs.get('args') == (event.pk, enums.EVENT)
                        or (c.args and c.args[1:] == ((event.pk, enums.EVENT),))]
        self.assertTrue(queued_calls, 'expected adjust_reminder_times to be queued for the event')

    def test_caches_invalidated_for_courses_and_external_calendars(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # Patch after fixture setup so post_save signals on Course (which themselves clear the
        # cache) don't pollute the call count we're asserting against.
        with mock.patch(
                'helium.planner.services.calendarservice.coursescheduleservice.clear_cached_course_schedule'
        ) as mock_clear_course_cache:
            # WHEN
            calendarservice.normalize_all_day_for_timezone_change(
                user, 'America/Chicago', 'America/Los_Angeles'
            )

            # THEN
            mock_clear_course_cache.assert_called_once_with(course)
