from datetime import timezone
from unittest import TestCase

from helium.planner.views.base import _parse_date_param_to_utc


class TestCaseParseDateParamToUtc(TestCase):
    def test_date_only_string_chicago_timezone(self):
        result = _parse_date_param_to_utc("2026-02-02", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 6)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_string_utc_timezone(self):
        result = _parse_date_param_to_utc("2026-02-02", "UTC")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 0)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_string_tokyo_timezone(self):
        result = _parse_date_param_to_utc("2026-02-02", "Asia/Tokyo")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 15)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_datetime_with_timezone_preserved(self):
        result = _parse_date_param_to_utc("2026-02-02T17:00:00Z", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 17)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_datetime_with_offset_converted_to_utc(self):
        # 17:00 in UTC-5 = 22:00 UTC
        result = _parse_date_param_to_utc("2026-02-02T17:00:00-05:00", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 22)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_during_dst(self):
        result = _parse_date_param_to_utc("2026-06-01", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 5)
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_different_timezones_same_date_different_utc(self):
        chicago_result = _parse_date_param_to_utc("2026-02-02", "America/Chicago")
        utc_result = _parse_date_param_to_utc("2026-02-02", "UTC")

        # Both should be Feb 2 in their local interpretation
        self.assertEqual(chicago_result.day, 2)
        self.assertEqual(utc_result.day, 2)

        # But the UTC hours should differ
        self.assertEqual(chicago_result.hour, 6)
        self.assertEqual(utc_result.hour, 0)

        # The difference should be 6 hours
        diff = chicago_result - utc_result
        self.assertEqual(diff.total_seconds(), 6 * 3600)
