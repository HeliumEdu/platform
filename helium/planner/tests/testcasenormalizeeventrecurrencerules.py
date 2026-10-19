import datetime
import importlib

from django.apps import apps
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Event
from helium.planner.tests.helpers import eventhelper

migration = importlib.import_module('helium.planner.migrations.0072_normalize_event_recurrence_rules')


class TestCaseNormalizeEventRecurrenceRules(TestCase):
    def test_rewrites_rules_sfcalendar_cannot_expand_into_ones_it_can(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        ordinal = eventhelper.given_event_exists(user, recurrence_rule='FREQ=MONTHLY;BYDAY=2TU')
        yearly = eventhelper.given_event_exists(user, recurrence_rule='FREQ=YEARLY;BYMONTH=11;BYDAY=4TH')

        # WHEN
        migration.normalize_event_recurrence_rules(apps, None)

        # THEN
        ordinal.refresh_from_db()
        yearly.refresh_from_db()
        self.assertEqual(ordinal.recurrence_rule, 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2')
        self.assertEqual(yearly.recurrence_rule, 'FREQ=YEARLY;BYMONTH=11;BYDAY=TH;BYSETPOS=4')

    def test_infers_implied_day_from_start_in_users_zone(self):
        for zone_name, expected in (('Europe/Amsterdam', 'FREQ=MONTHLY;BYMONTHDAY=14'),
                                    ('America/Los_Angeles', 'FREQ=MONTHLY;BYMONTHDAY=13')):
            with self.subTest(zone=zone_name):
                # GIVEN
                user = userhelper.given_a_user_exists(username=f'user_{zone_name}', email=f'{zone_name}@test.com')
                user.settings.time_zone = zone_name
                user.settings.save()
                start = datetime.datetime(2026, 10, 13, 23, 30, tzinfo=datetime.timezone.utc)
                event = eventhelper.given_event_exists(user, start=start, end=start + datetime.timedelta(hours=1),
                                                       recurrence_rule='FREQ=MONTHLY')

                # WHEN
                migration.normalize_event_recurrence_rules(apps, None)

                # THEN
                event.refresh_from_db()
                self.assertEqual(event.recurrence_rule, expected)

    def test_drops_rules_sfcalendar_cannot_expand_even_normalized(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user, recurrence_rule='FREQ=MONTHLY;BYDAY=MO,WE')

        # WHEN
        migration.normalize_event_recurrence_rules(apps, None)

        # THEN
        event.refresh_from_db()
        self.assertIsNone(event.recurrence_rule, 'the event is kept as a single occurrence')

    def test_leaves_supported_and_empty_rules_alone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        rules = ('FREQ=WEEKLY;BYDAY=MO', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2', 'FREQ=DAILY;COUNT=5', '', None)
        events = [eventhelper.given_event_exists(user, recurrence_rule=rule) for rule in rules]

        # WHEN
        migration.normalize_event_recurrence_rules(apps, None)

        # THEN
        for event, rule in zip(events, rules):
            event.refresh_from_db()
            self.assertEqual(event.recurrence_rule, rule)
