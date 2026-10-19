import datetime
from zoneinfo import ZoneInfo

import icalendar
from django.test import SimpleTestCase

from helium.feed.services import icalparseservice


def _local_dates(values, tz):
    return [value.astimezone(tz).date().isoformat() for value in values]


class TestCaseIcalParseService(SimpleTestCase):
    def test_all_day_dates_anchor_in_user_zone_not_feed_vtimezone(self):
        for feed_zone, user_zone in (('America/New_York', 'America/Los_Angeles'),
                                     ('Europe/Amsterdam', 'Asia/Tokyo')):
            with self.subTest(feed=feed_zone, user=user_zone):
                # GIVEN
                calendar = icalendar.Calendar.from_ical(
                    'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n'
                    f'BEGIN:VTIMEZONE\r\nTZID:{feed_zone}\r\nEND:VTIMEZONE\r\n'
                    'BEGIN:VEVENT\r\nUID:series-1\r\nSUMMARY:Reading\r\n'
                    'DTSTART;VALUE=DATE:20251006\r\nDTEND;VALUE=DATE:20251007\r\n'
                    'RRULE:FREQ=WEEKLY;COUNT=4;BYDAY=MO\r\nEXDATE;VALUE=DATE:20251013\r\n'
                    'RDATE;VALUE=DATE:20251108\r\nEND:VEVENT\r\n'
                    'BEGIN:VEVENT\r\nUID:series-1\r\nSUMMARY:Reading (moved)\r\n'
                    'RECURRENCE-ID;VALUE=DATE:20251020\r\nDTSTART;VALUE=DATE:20251021\r\n'
                    'DTEND;VALUE=DATE:20251022\r\nEND:VEVENT\r\n'
                    'BEGIN:VEVENT\r\nUID:timed-1\r\nSUMMARY:Lecture\r\n'
                    f'DTSTART;TZID={feed_zone}:20251006T090000\r\n'
                    f'DTEND;TZID={feed_zone}:20251006T100000\r\nEND:VEVENT\r\n'
                    'END:VCALENDAR\r\n')
                user_tz = ZoneInfo(user_zone)

                # WHEN
                parsed = {p['title']: p for p in icalparseservice.parse_events(calendar, user_tz)}

                # THEN
                series = parsed['Reading']
                self.assertEqual(_local_dates([series['start'], series['end']], user_tz), ['2025-10-06', '2025-10-07'])
                self.assertEqual(_local_dates((datetime.datetime.fromisoformat(v) for v in series['exception_dates']), user_tz),
                                 ['2025-10-13', '2025-10-20'])
                for exception_date in series['exception_dates']:
                    local_exception = datetime.datetime.fromisoformat(exception_date).astimezone(user_tz)
                    self.assertEqual(local_exception.time(), datetime.time(0, 0))
                    self.assertEqual(exception_date, local_exception.astimezone(datetime.timezone.utc).isoformat())
                self.assertEqual(_local_dates(series['extra_starts'], user_tz), ['2025-11-08'])
                self.assertEqual(series['start'].astimezone(user_tz).time(), datetime.time(0, 0))
                timed = parsed['Lecture']
                self.assertEqual(timed['start'],
                                 datetime.datetime(2025, 10, 6, 9, 0, tzinfo=ZoneInfo(feed_zone)))

    def test_monthly_ordinal_rrule_normalized_to_bysetpos(self):
        # GIVEN
        calendar = _calendar_with_rrule('FREQ=MONTHLY;BYDAY=2TU', 'DTSTART;TZID=America/New_York:20261013T090000')

        # WHEN
        parsed = next(icalparseservice.parse_events(calendar, ZoneInfo('America/New_York')))

        # THEN
        self.assertEqual(parsed['recurrence_rule'], 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2')

    def test_rrule_sfcalendar_cannot_expand_dropped(self):
        for rule in ('FREQ=MONTHLY;BYDAY=MO,WE', 'FREQ=MONTHLY;BYDAY=TU', 'FREQ=YEARLY;BYMONTHDAY=15'):
            with self.subTest(rule=rule):
                # GIVEN
                calendar = _calendar_with_rrule(rule, 'DTSTART;TZID=America/New_York:20261013T090000')

                # WHEN
                parsed = next(icalparseservice.parse_events(calendar, ZoneInfo('America/New_York')))

                # THEN
                self.assertIsNone(parsed['recurrence_rule'], 'the event is kept as a single occurrence')
                self.assertEqual(parsed['source_recurrence_rule'], rule)

    def test_inferred_rrule_day_follows_user_zone_not_feed_zone(self):
        for user_zone, expected_weekly, expected_monthly in (
                ('Europe/Amsterdam', 'FREQ=WEEKLY;BYDAY=WE', 'FREQ=MONTHLY;BYMONTHDAY=14'),
                ('America/Los_Angeles', 'FREQ=WEEKLY;BYDAY=TU', 'FREQ=MONTHLY;BYMONTHDAY=13')):
            for rule, expected in (('FREQ=WEEKLY', expected_weekly), ('FREQ=MONTHLY', expected_monthly)):
                with self.subTest(user=user_zone, rule=rule):
                    # GIVEN
                    calendar = _calendar_with_rrule(rule, 'DTSTART;TZID=America/New_York:20261013T210000',
                                                    feed_zone='America/New_York')

                    # WHEN
                    parsed = next(icalparseservice.parse_events(calendar, ZoneInfo(user_zone)))

                    # THEN
                    self.assertEqual(parsed['recurrence_rule'], expected,
                                     'the client expands in the user\'s zone, so the implied day is the local one')

    def test_all_day_yearly_rrule_infers_month_and_day_from_date(self):
        # GIVEN
        calendar = _calendar_with_rrule('FREQ=YEARLY', 'DTSTART;VALUE=DATE:20261013')

        # WHEN
        parsed = next(icalparseservice.parse_events(calendar, ZoneInfo('Asia/Tokyo')))

        # THEN
        self.assertEqual(parsed['recurrence_rule'], 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13')


def _calendar_with_rrule(rule, dtstart_line, feed_zone=None):
    vtimezone = f'BEGIN:VTIMEZONE\r\nTZID:{feed_zone}\r\nEND:VTIMEZONE\r\n' if feed_zone else ''
    return icalendar.Calendar.from_ical(
        'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n'
        f'{vtimezone}'
        'BEGIN:VEVENT\r\nUID:series-1\r\nSUMMARY:Series\r\n'
        f'{dtstart_line}\r\n'
        f'RRULE:{rule}\r\nEND:VEVENT\r\n'
        'END:VCALENDAR\r\n')
