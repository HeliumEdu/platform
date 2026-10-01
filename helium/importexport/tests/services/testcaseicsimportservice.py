import datetime
from zoneinfo import ZoneInfo

import icalendar
from django.test import SimpleTestCase

from helium.feed.services import icalparseservice
from helium.importexport.services import icsimportservice

class TestCaseAssignmentStartTimes(SimpleTestCase):
    def test_expansion_stops_on_the_user_local_course_end(self):
        amsterdam = ZoneInfo('Europe/Amsterdam')
        parsed = {
            'start': datetime.datetime(2025, 9, 15, 22, 30, tzinfo=datetime.timezone.utc),
            'recurrence_rule': 'FREQ=DAILY',
            'exception_dates': None,
            'extra_starts': [],
        }

        # WHEN
        starts = icsimportservice._assignment_start_times(
            parsed, datetime.date(2025, 9, 18), amsterdam)

        local_dates = [s.astimezone(amsterdam).date() for s in starts]
        self.assertNotIn(datetime.date(2025, 9, 19), local_dates)
        self.assertEqual(
            [datetime.date(2025, 9, 16), datetime.date(2025, 9, 17),
             datetime.date(2025, 9, 18)],
            local_dates)

    def test_expansion_keeps_the_final_local_day_at_a_negative_offset(self):
        los_angeles = ZoneInfo('America/Los_Angeles')
        parsed = {
            'start': datetime.datetime(2025, 9, 17, 6, 0, tzinfo=datetime.timezone.utc),
            'recurrence_rule': 'FREQ=DAILY',
            'exception_dates': None,
            'extra_starts': [],
        }

        # WHEN
        starts = icsimportservice._assignment_start_times(
            parsed, datetime.date(2025, 9, 18), los_angeles)

        # THEN
        local_dates = [s.astimezone(los_angeles).date() for s in starts]
        self.assertIn(datetime.date(2025, 9, 18), local_dates)

    def test_weekly_expansion_keeps_the_local_wall_clock_across_dst(self):
        for zone_name, first_start_utc in (('Europe/Berlin', datetime.datetime(2026, 10, 14, 7, 0)),
                                           ('America/Chicago', datetime.datetime(2026, 10, 21, 14, 0))):
            with self.subTest(zone=zone_name):
                # GIVEN
                zone = ZoneInfo(zone_name)
                parsed = {
                    'start': first_start_utc.replace(tzinfo=datetime.timezone.utc),
                    'recurrence_rule': 'FREQ=WEEKLY;COUNT=4;BYDAY=WE',
                    'exception_dates': None,
                    'extra_starts': [],
                }

                # WHEN
                starts = icsimportservice._assignment_start_times(
                    parsed, datetime.date(2026, 12, 31), zone)

                # THEN
                local_starts = [s.astimezone(zone) for s in starts]
                self.assertEqual(4, len(local_starts))
                self.assertEqual({(2, 9, 0)}, {(s.weekday(), s.hour, s.minute) for s in local_starts})
                self.assertTrue(all(s.tzinfo == datetime.timezone.utc for s in starts))

    def test_series_with_utc_until_expands_every_weekly_occurrence(self):
        for zone_name in ('Europe/Amsterdam', 'America/Los_Angeles'):
            with self.subTest(zone=zone_name):
                # GIVEN
                calendar = icalendar.Calendar.from_ical(
                    'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n'
                    f'BEGIN:VTIMEZONE\r\nTZID:{zone_name}\r\nEND:VTIMEZONE\r\n'
                    'BEGIN:VEVENT\r\nUID:quiz-1\r\nSUMMARY:Quiz\r\n'
                    f'DTSTART;TZID={zone_name}:20261014T090000\r\n'
                    f'DTEND;TZID={zone_name}:20261014T100000\r\n'
                    'RRULE:FREQ=WEEKLY;UNTIL=20261126T000000Z;BYDAY=WE\r\nEND:VEVENT\r\n'
                    'END:VCALENDAR\r\n')
                zone = ZoneInfo(zone_name)
                parsed = next(icalparseservice.parse_events(calendar, zone))

                # WHEN
                starts = icsimportservice._assignment_start_times(parsed, datetime.date(2026, 12, 31), zone)

                # THEN
                self.assertEqual(parsed['recurrence_rule'], 'FREQ=WEEKLY;UNTIL=20261126T000000Z;BYDAY=WE')
                self.assertEqual(len(starts), 7, 'every Wednesday from Oct 14 through Nov 25')
