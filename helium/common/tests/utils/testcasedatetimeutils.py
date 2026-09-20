import datetime

from django.test import TestCase

from helium.auth.models import UserSettings
from helium.common import enums
from helium.common.utils.datetimeutils import format_date, format_date_time, format_short_time, format_time


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
