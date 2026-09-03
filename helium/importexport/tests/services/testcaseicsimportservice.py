import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

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
