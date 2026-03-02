__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import timezone
from unittest import TestCase

from helium.planner.views.base import _parse_date_param_to_utc


class TestCaseParseDateParamToUtc(TestCase):
    """
    Tests for the _parse_date_param_to_utc helper function.

    This function ensures that date-only query parameters (e.g., "2026-02-02")
    are interpreted in the user's timezone, not the server's timezone. This is
    critical for consistent behavior when the server runs in different timezones
    (e.g., UTC on CI vs local dev machine timezone).
    """

    def test_date_only_string_chicago_timezone(self):
        """
        A date-only string should be interpreted as midnight in the user's timezone.
        For America/Chicago (CST, UTC-6), midnight Feb 2 = 06:00 UTC on Feb 2.
        """
        result = _parse_date_param_to_utc("2026-02-02", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 6)  # Midnight CST = 06:00 UTC
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_string_utc_timezone(self):
        """
        For a user in UTC, midnight Feb 2 = 00:00 UTC.
        """
        result = _parse_date_param_to_utc("2026-02-02", "UTC")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 0)  # Midnight UTC = 00:00 UTC
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_string_tokyo_timezone(self):
        """
        For Asia/Tokyo (JST, UTC+9), midnight Feb 2 JST = 15:00 UTC on Feb 1.
        """
        result = _parse_date_param_to_utc("2026-02-02", "Asia/Tokyo")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 1)  # Previous day in UTC
        self.assertEqual(result.hour, 15)  # Midnight JST = 15:00 UTC previous day
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_datetime_with_timezone_preserved(self):
        """
        If the input already has timezone info (ISO 8601 with Z suffix),
        it should be converted to UTC without using the user's timezone.
        """
        result = _parse_date_param_to_utc("2026-02-02T17:00:00Z", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 17)  # Already UTC, unchanged
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_datetime_with_offset_converted_to_utc(self):
        """
        If the input has an explicit offset, it should be converted to UTC.
        """
        # 17:00 in UTC-5 = 22:00 UTC
        result = _parse_date_param_to_utc("2026-02-02T17:00:00-05:00", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 2)
        self.assertEqual(result.hour, 22)  # 17:00 - (-5:00) = 22:00 UTC
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_date_only_during_dst(self):
        """
        During DST, America/Chicago is CDT (UTC-5).
        Midnight June 1 CDT = 05:00 UTC.
        """
        result = _parse_date_param_to_utc("2026-06-01", "America/Chicago")

        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 1)
        self.assertEqual(result.hour, 5)  # Midnight CDT = 05:00 UTC
        self.assertEqual(result.minute, 0)
        self.assertEqual(result.tzinfo, timezone.utc)

    def test_different_timezones_same_date_different_utc(self):
        """
        The same date-only string should produce different UTC times
        depending on the user's timezone. This is the core fix for the
        integration test failure.
        """
        chicago_result = _parse_date_param_to_utc("2026-02-02", "America/Chicago")
        utc_result = _parse_date_param_to_utc("2026-02-02", "UTC")

        # Both should be Feb 2 in their local interpretation
        self.assertEqual(chicago_result.day, 2)
        self.assertEqual(utc_result.day, 2)

        # But the UTC hours should differ
        self.assertEqual(chicago_result.hour, 6)  # CST offset
        self.assertEqual(utc_result.hour, 0)  # No offset

        # The difference should be 6 hours
        diff = chicago_result - utc_result
        self.assertEqual(diff.total_seconds(), 6 * 3600)
