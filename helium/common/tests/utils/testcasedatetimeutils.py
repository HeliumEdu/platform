import datetime
import itertools
from zoneinfo import ZoneInfo

from django.test import TestCase
from django.utils import timezone

from helium.auth.models import UserSettings
from helium.common import enums
from helium.common.utils.datetimeutils import expand_recurrence, format_date, format_date_time, format_short_time, \
    format_time, local_midnight_as_utc, occurrence_end, shift_exception_dates, shifted_series_bounds


class TestCaseDateTimeUtils(TestCase):
    def setUp(self):
        self.friday_afternoon = datetime.datetime(2026, 9, 4, 15, 5)
        self.friday_on_the_hour = datetime.datetime(2026, 9, 4, 15, 0)
        self.just_after_midnight = datetime.datetime(2026, 9, 4, 0, 5)
        self.us_settings = UserSettings()
        self.european_settings = UserSettings(date_format=enums.DMY, time_format=enums.TWENTY_FOUR_HOUR)

    def test_format_date_month_first(self):
        self.assertEqual(format_date(self.friday_afternoon, self.us_settings), 'Fri, Sep 4')

    def test_format_date_day_first(self):
        self.assertEqual(format_date(self.friday_afternoon, self.european_settings), 'Fri, 4 Sep')

    def test_format_time_twelve_hour_has_no_leading_zero(self):
        self.assertEqual(format_time(self.friday_afternoon, self.us_settings), '3:05 PM')
        self.assertEqual(format_time(self.just_after_midnight, self.us_settings), '12:05 AM')

    def test_format_time_twenty_four_hour_keeps_leading_zero(self):
        self.assertEqual(format_time(self.friday_afternoon, self.european_settings), '15:05')
        self.assertEqual(format_time(self.just_after_midnight, self.european_settings), '00:05')

    def test_format_time_omits_zero_minutes_only_on_twelve_hour_clock(self):
        self.assertEqual(format_time(self.friday_on_the_hour, self.us_settings, omit_zero_minutes=True), '3 PM')
        self.assertEqual(format_time(self.friday_on_the_hour, self.european_settings, omit_zero_minutes=True),
                         '15:00')

    def test_format_date_time(self):
        self.assertEqual(format_date_time(self.friday_afternoon, self.us_settings), 'Fri, Sep 4 at 3:05 PM')
        self.assertEqual(format_date_time(self.friday_afternoon, self.european_settings), 'Fri, 4 Sep at 15:05')

    def test_format_short_time(self):
        self.assertEqual(format_short_time(self.friday_on_the_hour, self.us_settings), 'Fri, 3 PM')
        self.assertEqual(format_short_time(self.friday_afternoon, self.us_settings), 'Fri, 3:05 PM')
        self.assertEqual(format_short_time(self.friday_on_the_hour, self.european_settings), 'Fri, 15:00')


class TestCaseExpandRecurrence(TestCase):
    def test_weekly_series_keeps_its_wall_clock_across_dst(self):
        for zone in ('Europe/Amsterdam', 'America/Los_Angeles'):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                start = datetime.datetime(2026, 10, 19, 9, 0, tzinfo=tz)

                # WHEN
                occurrences = list(itertools.islice(
                    expand_recurrence('FREQ=WEEKLY;BYDAY=MO', start, start + datetime.timedelta(hours=1), tz), 4))

                # THEN
                self.assertEqual([(s.astimezone(tz).date(), s.astimezone(tz).hour) for s, _ in occurrences],
                                 [(datetime.date(2026, 10, 19), 9), (datetime.date(2026, 10, 26), 9),
                                  (datetime.date(2026, 11, 2), 9), (datetime.date(2026, 11, 9), 9)])
                self.assertTrue(all(e - s == datetime.timedelta(hours=1) for s, e in occurrences))
                self.assertTrue(all(s.tzinfo == datetime.timezone.utc for s, _ in occurrences))

    def test_all_day_series_spans_local_midnights_across_dst(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        start = local_midnight_as_utc(datetime.date(2026, 10, 24), tz)
        end = local_midnight_as_utc(datetime.date(2026, 10, 26), tz)

        # WHEN
        occurrences = list(itertools.islice(expand_recurrence('FREQ=DAILY', start, end, tz, all_day=True), 3))

        # THEN
        self.assertEqual(occurrences, [
            (local_midnight_as_utc(datetime.date(2026, 10, 24), tz), local_midnight_as_utc(datetime.date(2026, 10, 26), tz)),
            (local_midnight_as_utc(datetime.date(2026, 10, 25), tz), local_midnight_as_utc(datetime.date(2026, 10, 27), tz)),
            (local_midnight_as_utc(datetime.date(2026, 10, 26), tz), local_midnight_as_utc(datetime.date(2026, 10, 28), tz)),
        ])
        self.assertEqual(occurrences[1][1] - occurrences[1][0], datetime.timedelta(hours=49))

    def test_exception_skips_the_occurrence_on_its_local_date(self):
        for zone, exception in (('Pacific/Auckland', '2026-09-07T20:00:00Z'),
                                ('America/Los_Angeles', '2026-09-08T23:00:00Z')):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                start = datetime.datetime(2026, 9, 1, 8, 0, tzinfo=tz)

                # WHEN
                dates = [s.astimezone(tz).date() for s, _ in itertools.islice(
                    expand_recurrence('FREQ=DAILY', start, start, tz, exception_dates=[exception]), 9)]

                # THEN
                self.assertNotIn(datetime.date(2026, 9, 8), dates)
                self.assertEqual(dates[6:8], [datetime.date(2026, 9, 7), datetime.date(2026, 9, 9)])

    def test_date_only_until_includes_the_whole_local_day_for_a_timed_series(self):
        # GIVEN
        tz = ZoneInfo('America/Los_Angeles')
        start = datetime.datetime(2026, 9, 1, 21, 30, tzinfo=tz)

        # WHEN
        occurrences = list(expand_recurrence('FREQ=DAILY;UNTIL=20260903', start, start, tz))

        # THEN
        self.assertEqual([s.astimezone(tz).date() for s, _ in occurrences],
                         [datetime.date(2026, 9, 1), datetime.date(2026, 9, 2), datetime.date(2026, 9, 3)])

    def test_utc_until_is_compared_as_an_instant(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        start = datetime.datetime(2026, 9, 1, 9, 0, tzinfo=tz)

        # WHEN
        occurrences = list(expand_recurrence('FREQ=DAILY;UNTIL=20260903T065959Z', start, start, tz))

        # THEN
        self.assertEqual([s.astimezone(tz).date() for s, _ in occurrences],
                         [datetime.date(2026, 9, 1), datetime.date(2026, 9, 2)])

    def test_not_before_drops_earlier_occurrences(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        start = datetime.datetime(2026, 9, 1, 9, 0, tzinfo=tz)
        not_before = datetime.datetime(2026, 9, 3, 9, 0, tzinfo=tz)

        # WHEN
        first = next(expand_recurrence('FREQ=DAILY', start, start, tz, not_before=not_before))

        # THEN
        self.assertEqual(first[0], not_before.astimezone(datetime.timezone.utc))

    def test_rule_that_never_produces_a_date_yields_nothing(self):
        # GIVEN
        tz = ZoneInfo('America/Los_Angeles')
        start = datetime.datetime(2026, 9, 1, 9, 0, tzinfo=tz)

        # WHEN
        occurrences = list(expand_recurrence('FREQ=DAILY;BYMONTH=2;BYMONTHDAY=30', start, start, tz))

        # THEN
        self.assertEqual(occurrences, [])

    def test_endless_series_stops_at_the_horizon(self):
        # GIVEN
        tz = ZoneInfo('America/Chicago')
        start = timezone.now() - datetime.timedelta(days=1)

        # WHEN
        occurrences = list(expand_recurrence('FREQ=YEARLY', start, start, tz))

        # THEN
        self.assertEqual(len(occurrences), enums.RECURRENCE_HORIZON_YEARS + 1)

    def test_occurrence_past_the_horizon_is_not_found(self):
        # GIVEN
        tz = ZoneInfo('America/Chicago')
        start = timezone.now()
        not_before = datetime.datetime(9999, 1, 1, tzinfo=datetime.timezone.utc)

        # WHEN
        first = next(expand_recurrence('FREQ=DAILY', start, start, tz, not_before=not_before), None)

        # THEN
        self.assertIsNone(first)


class TestCaseOccurrenceEnd(TestCase):
    def test_timed_occurrence_keeps_the_first_occurrence_duration(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        first_start = datetime.datetime(2026, 10, 19, 9, 0, tzinfo=tz)
        occurrence_start = datetime.datetime(2026, 10, 26, 9, 0, tzinfo=tz)

        # WHEN
        end = occurrence_end(first_start, first_start + datetime.timedelta(minutes=90), occurrence_start, tz)

        # THEN
        self.assertEqual(end, (occurrence_start + datetime.timedelta(minutes=90)).astimezone(datetime.timezone.utc))

    def test_all_day_occurrence_keeps_its_span_of_dates_across_dst(self):
        # GIVEN
        tz = ZoneInfo('America/Los_Angeles')
        first_start = local_midnight_as_utc(datetime.date(2026, 10, 31), tz)
        first_end = local_midnight_as_utc(datetime.date(2026, 11, 1), tz)

        # WHEN
        end = occurrence_end(first_start, first_end, first_end, tz, all_day=True)

        # THEN
        self.assertEqual(end, local_midnight_as_utc(datetime.date(2026, 11, 2), tz))
        self.assertEqual(end - first_end, datetime.timedelta(hours=25))


class TestCaseShiftedSeriesBounds(TestCase):
    def test_series_moves_by_the_occurrence_day_shift_to_the_new_wall_clock(self):
        for zone in ('Europe/Amsterdam', 'America/Los_Angeles'):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                series_start = datetime.datetime(2026, 10, 5, 9, 0, tzinfo=tz)
                occurrence_start = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=tz)
                new_start = datetime.datetime(2026, 11, 3, 14, 30, tzinfo=tz)

                # WHEN
                start, end = shifted_series_bounds(series_start, occurrence_start, new_start,
                                                   new_start + datetime.timedelta(hours=2), tz)

                # THEN
                self.assertEqual(start.astimezone(tz).replace(tzinfo=None), datetime.datetime(2026, 10, 6, 14, 30))
                self.assertEqual(end - start, datetime.timedelta(hours=2))

    def test_all_day_series_moves_to_local_midnight_with_the_new_span(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        series_start = local_midnight_as_utc(datetime.date(2026, 10, 5), tz)
        occurrence_start = local_midnight_as_utc(datetime.date(2026, 10, 19), tz)
        new_start = local_midnight_as_utc(datetime.date(2026, 10, 21), tz)

        # WHEN
        start, end = shifted_series_bounds(series_start, occurrence_start, new_start,
                                           local_midnight_as_utc(datetime.date(2026, 10, 23), tz), tz, all_day=True)

        # THEN
        self.assertEqual(start, local_midnight_as_utc(datetime.date(2026, 10, 7), tz))
        self.assertEqual(end, local_midnight_as_utc(datetime.date(2026, 10, 9), tz))


class TestCaseShiftExceptionDates(TestCase):
    def test_exceptions_move_by_the_wall_clock_distance_across_dst(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        old_start = datetime.datetime(2026, 10, 19, 9, 0, tzinfo=tz)
        new_start = datetime.datetime(2026, 10, 20, 10, 0, tzinfo=tz)
        exception = datetime.datetime(2026, 11, 2, 9, 0, tzinfo=tz).astimezone(datetime.timezone.utc)

        # WHEN
        shifted = shift_exception_dates([exception.isoformat()], old_start, new_start, tz)

        # THEN
        self.assertEqual(shifted, ['2026-11-03T09:00:00Z'])

    def test_no_exceptions_returned_as_given(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        start = datetime.datetime(2026, 10, 19, 9, 0, tzinfo=tz)

        # WHEN
        shifted = shift_exception_dates(None, start, start + datetime.timedelta(days=1), tz)

        # THEN
        self.assertIsNone(shifted)
