import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common.utils import validators
from helium.common.utils.validators import (
    infer_byday_for_weekly_rrule,
    validate_fraction,
    validate_quill_delta,
    validate_recurrence_rule,
)


class TestCaseValidateFraction(TestCase):
    def test_zero_denominator_rejected(self):
        with self.assertRaises(ValidationError):
            validate_fraction('5/0')

    def test_zero_over_zero_rejected(self):
        with self.assertRaises(ValidationError):
            validate_fraction('0/0')

    def test_negative_denominator_rejected(self):
        with self.assertRaises(ValidationError):
            validate_fraction('5/-10')

    def test_ungraded_sentinel_passes(self):
        self.assertEqual(validate_fraction('-1/100'), '-1/100')

    def test_zero_earned_passes(self):
        self.assertEqual(validate_fraction('0/100'), '0/100')

    def test_valid_fraction_passes(self):
        self.assertEqual(validate_fraction('75/100'), '75/100')

    def test_invalid_format_rejected(self):
        with self.assertRaises(ValidationError):
            validate_fraction('not-a-fraction')

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValidationError):
            validate_fraction('abc/def')


class TestCaseValidateQuillDelta(TestCase):
    def test_none_passes(self):
        validate_quill_delta(None)

    def test_empty_ops_passes(self):
        validate_quill_delta({'ops': []})

    def test_canonical_empty_doc_passes(self):
        validate_quill_delta({'ops': [{'insert': '\n'}]})

    def test_simple_doc_passes(self):
        validate_quill_delta({'ops': [{'insert': 'hello world\n'}]})

    def test_bare_string_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quill_delta('this is just a string')

    def test_bare_int_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quill_delta(12345)

    def test_empty_dict_passes(self):
        validate_quill_delta({})

    def test_missing_ops_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quill_delta({'title': 'no ops here'})

    def test_non_list_ops_rejected(self):
        with self.assertRaises(ValidationError):
            validate_quill_delta({'ops': 'not-a-list'})


class TestCaseValidateRecurrenceRule(TestCase):
    def test_valid_rrule_passes(self):
        validate_recurrence_rule('FREQ=WEEKLY;BYDAY=MO,WE,FR')
        validate_recurrence_rule('FREQ=WEEKLY;UNTIL=20261126T000000Z;BYDAY=WE')
        validate_recurrence_rule('FREQ=WEEKLY;UNTIL=20261126T000000;BYDAY=WE')

    def test_unsupported_freq_rejected(self):
        with self.assertRaises(ValidationError):
            validate_recurrence_rule('FREQ=HOURLY;COUNT=5')

    def test_unsupported_part_rejected(self):
        with self.assertRaises(ValidationError):
            validate_recurrence_rule('FREQ=WEEKLY;BYDAY=MO;WKST=SU')

    def test_monthly_and_yearly_rules_sfcalendar_expands_pass(self):
        for rule in ('FREQ=MONTHLY;BYMONTHDAY=15', 'FREQ=MONTHLY;BYMONTHDAY=-1', 'FREQ=MONTHLY;BYMONTHDAY=31',
                     'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2', 'FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1',
                     'FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-2', 'FREQ=MONTHLY;INTERVAL=2;BYMONTHDAY=1;COUNT=6',
                     'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13', 'FREQ=YEARLY;BYMONTH=11;BYDAY=TH;BYSETPOS=4',
                     'RRULE:FREQ=MONTHLY;BYMONTHDAY=1'):
            with self.subTest(rule=rule):
                # WHEN
                validate_recurrence_rule(rule)

    def test_monthly_and_yearly_rules_normalization_rewrites_pass(self):
        for rule in ('FREQ=MONTHLY;BYDAY=2TU', 'FREQ=MONTHLY;BYDAY=-1FR', 'FREQ=MONTHLY;BYDAY=+3WE',
                     'FREQ=MONTHLY', 'FREQ=YEARLY', 'FREQ=YEARLY;BYMONTH=3', 'FREQ=YEARLY;BYMONTH=11;BYDAY=4TH',
                     'freq=monthly;byday=2tu'):
            with self.subTest(rule=rule):
                # WHEN
                validate_recurrence_rule(rule)

    def test_monthly_and_yearly_rules_sfcalendar_cannot_expand_rejected(self):
        for rule in ('FREQ=MONTHLY;BYDAY=TU', 'FREQ=MONTHLY;BYDAY=MO,WE', 'FREQ=MONTHLY;BYDAY=1MO,3MO',
                     'FREQ=MONTHLY;BYDAY=5FR', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=5',
                     'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=-3', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=1,3',
                     'FREQ=MONTHLY;BYDAY=2TU;BYSETPOS=2', 'FREQ=MONTHLY;BYSETPOS=2',
                     'FREQ=MONTHLY;BYDAY=FR;BYMONTHDAY=13', 'FREQ=MONTHLY;BYMONTHDAY=1,15',
                     'FREQ=MONTHLY;BYMONTHDAY=-2', 'FREQ=MONTHLY;BYMONTH=3', 'FREQ=YEARLY;BYMONTHDAY=15',
                     'FREQ=YEARLY;BYDAY=20MO', 'FREQ=YEARLY;BYDAY=TH;BYSETPOS=4',
                     'FREQ=YEARLY;BYMONTH=11;BYDAY=TH', 'FREQ=YEARLY;BYMONTH=1,6;BYMONTHDAY=1'):
            with self.subTest(rule=rule):
                # WHEN
                with self.assertRaises(ValidationError) as raised:
                    validate_recurrence_rule(rule)

                # THEN
                self.assertTrue(raised.exception.messages)

    def test_daily_and_weekly_rules_unaffected_by_monthly_and_yearly_checks(self):
        for rule in ('FREQ=DAILY', 'FREQ=DAILY;INTERVAL=2;COUNT=10', 'FREQ=WEEKLY',
                     'FREQ=WEEKLY;BYDAY=MO,WE,FR', 'FREQ=WEEKLY;INTERVAL=2;BYDAY=TU'):
            with self.subTest(rule=rule):
                # WHEN
                validate_recurrence_rule(rule)


class TestCasePrepareRecurrenceRule(TestCase):
    _TUESDAY_THE_13TH = datetime.datetime(2026, 10, 13, 9, 0)

    def test_returns_normalized_rule(self):
        for rule, expected in (('FREQ=MONTHLY;BYDAY=2TU', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2'),
                               ('FREQ=YEARLY', 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13'),
                               ('FREQ=WEEKLY', 'FREQ=WEEKLY;BYDAY=TU'),
                               ('FREQ=DAILY;COUNT=5', 'FREQ=DAILY;COUNT=5')):
            with self.subTest(rule=rule):
                # WHEN
                prepared = validators.prepare_recurrence_rule(rule, self._TUESDAY_THE_13TH)

                # THEN
                self.assertEqual(prepared, expected)

    def test_rule_sfcalendar_cannot_expand_even_normalized_raises(self):
        for rule in ('FREQ=MONTHLY;BYDAY=MO,WE', 'FREQ=MONTHLY;BYDAY=5FR', 'FREQ=YEARLY;BYMONTHDAY=15',
                     'FREQ=HOURLY;COUNT=5', 'FREQ=WEEKLY;BYDAY=MO;WKST=SU', 'FREQ=NOPE;BANANA'):
            with self.subTest(rule=rule):
                # WHEN
                with self.assertRaises(ValidationError) as raised:
                    validators.prepare_recurrence_rule(rule, self._TUESDAY_THE_13TH)

                # THEN
                self.assertTrue(raised.exception.messages)


class TestCaseNormalizeRecurrenceRuleForUser(TestCase):
    def test_infers_implied_day_from_start_in_users_zone(self):
        for zone_name, expected in (('Europe/Amsterdam', 'FREQ=MONTHLY;BYMONTHDAY=14'),
                                    ('America/Los_Angeles', 'FREQ=MONTHLY;BYMONTHDAY=13')):
            with self.subTest(zone=zone_name):
                # GIVEN
                user = userhelper.given_a_user_exists(username=f'user_{zone_name}', email=f'{zone_name}@test.com')
                user.settings.time_zone = zone_name
                user.settings.save()
                start = datetime.datetime(2026, 10, 13, 23, 30, tzinfo=datetime.timezone.utc)

                # WHEN
                normalized = validators.normalize_recurrence_rule_for_user('FREQ=MONTHLY', start, user)

                # THEN
                self.assertEqual(normalized, expected)

    def test_missing_rule_or_start_returned_unchanged(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        start = datetime.datetime(2026, 10, 13, 16, 0, tzinfo=datetime.timezone.utc)

        for rule, rule_start in ((None, start), ('', start), ('FREQ=MONTHLY', None)):
            with self.subTest(rule=rule, start=rule_start):
                # WHEN
                normalized = validators.normalize_recurrence_rule_for_user(rule, rule_start, user)

                # THEN
                self.assertEqual(normalized, rule)


class TestCaseNormalizeRecurrenceRule(TestCase):
    _TUESDAY_THE_13TH = datetime.datetime(2026, 10, 13, 9, 0)

    def _assert_normalizes(self, cases, local_start=_TUESDAY_THE_13TH):
        for rule, expected in cases:
            with self.subTest(rule=rule):
                # WHEN
                normalized = validators.normalize_recurrence_rule(rule, local_start)

                # THEN
                self.assertEqual(normalized, expected)

    def test_monthly_ordinal_byday_split_into_byday_and_bysetpos(self):
        self._assert_normalizes((('FREQ=MONTHLY;BYDAY=2TU', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2'),
                                 ('FREQ=MONTHLY;BYDAY=-1FR', 'FREQ=MONTHLY;BYDAY=FR;BYSETPOS=-1'),
                                 ('FREQ=MONTHLY;BYDAY=+3WE', 'FREQ=MONTHLY;BYDAY=WE;BYSETPOS=3'),
                                 ('FREQ=MONTHLY;BYDAY=-2MO', 'FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-2')))

    def test_yearly_ordinal_byday_split_into_byday_and_bysetpos(self):
        self._assert_normalizes((('FREQ=YEARLY;BYMONTH=11;BYDAY=4TH', 'FREQ=YEARLY;BYMONTH=11;BYDAY=TH;BYSETPOS=4'),))

    def test_monthly_without_day_infers_month_day_from_start(self):
        self._assert_normalizes((('FREQ=MONTHLY', 'FREQ=MONTHLY;BYMONTHDAY=13'),
                                 ('FREQ=MONTHLY;INTERVAL=2;COUNT=6', 'FREQ=MONTHLY;INTERVAL=2;COUNT=6;BYMONTHDAY=13')))

    def test_yearly_without_month_or_day_infers_both_from_start(self):
        self._assert_normalizes((('FREQ=YEARLY', 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13'),))

    def test_yearly_with_month_only_infers_month_day_from_start(self):
        self._assert_normalizes((('FREQ=YEARLY;BYMONTH=3', 'FREQ=YEARLY;BYMONTH=3;BYMONTHDAY=13'),))

    def test_inferred_day_and_month_are_those_of_the_start_given(self):
        self._assert_normalizes((('FREQ=YEARLY', 'FREQ=YEARLY;BYMONTH=12;BYMONTHDAY=31'),),
                                local_start=datetime.datetime(2026, 12, 31, 23, 30))

    def test_rules_sfcalendar_expands_returned_unchanged(self):
        self._assert_normalizes((rule, rule) for rule in (
            'FREQ=MONTHLY;BYMONTHDAY=15', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2', 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13',
            'FREQ=YEARLY;BYMONTH=11;BYDAY=TH;BYSETPOS=4', 'FREQ=DAILY;COUNT=5', 'FREQ=WEEKLY;BYDAY=MO,WE'))

    def test_weekly_without_byday_infers_weekday_from_start(self):
        self._assert_normalizes((('FREQ=WEEKLY', 'FREQ=WEEKLY;BYDAY=TU'),))

    def test_lowercase_weekly_without_byday_infers_weekday_from_start(self):
        self._assert_normalizes((('freq=weekly', 'FREQ=WEEKLY;BYDAY=TU'),))

    def test_rrule_prefix_and_other_parts_preserved(self):
        self._assert_normalizes((('RRULE:FREQ=MONTHLY;BYDAY=2TU;UNTIL=20270101T000000Z',
                                  'RRULE:FREQ=MONTHLY;BYDAY=TU;UNTIL=20270101T000000Z;BYSETPOS=2'),))

    def test_lowercase_monthly_rule_uppercased(self):
        self._assert_normalizes((('freq=monthly;byday=2tu', 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2'),))

    def test_empty_rule_returned_unchanged(self):
        self._assert_normalizes(((None, None), ('', '')))

    def test_ordinal_byday_with_bysetpos_left_for_validation_to_reject(self):
        # GIVEN
        rule = 'FREQ=MONTHLY;BYDAY=2TU;BYSETPOS=2'

        # WHEN
        normalized = validators.normalize_recurrence_rule(rule, self._TUESDAY_THE_13TH)

        # THEN
        self.assertEqual(normalized, rule)
        with self.assertRaises(ValidationError):
            validate_recurrence_rule(normalized)

    def test_multiple_weekdays_left_for_validation_to_reject(self):
        # GIVEN
        rule = 'FREQ=MONTHLY;BYDAY=1MO,3MO'

        # WHEN
        normalized = validators.normalize_recurrence_rule(rule, self._TUESDAY_THE_13TH)

        # THEN
        self.assertEqual(normalized, rule)
        with self.assertRaises(ValidationError):
            validate_recurrence_rule(normalized)


class TestCaseInferBydayForWeeklyRrule(TestCase):
    def test_weekly_with_byday_returned_unchanged(self):
        rule = 'FREQ=WEEKLY;BYDAY=WE'
        self.assertEqual(infer_byday_for_weekly_rrule(rule, datetime.datetime(2025, 9, 1)), rule)

    def test_weekly_without_byday_infers_from_dtstart(self):
        # 2025-09-01 is a Monday (weekday 0)
        self.assertEqual(
            infer_byday_for_weekly_rrule('FREQ=WEEKLY', datetime.datetime(2025, 9, 1)),
            'FREQ=WEEKLY;BYDAY=MO',
        )

    def test_rrule_prefix_preserved(self):
        self.assertEqual(
            infer_byday_for_weekly_rrule('RRULE:FREQ=WEEKLY', datetime.datetime(2025, 9, 1)),
            'RRULE:FREQ=WEEKLY;BYDAY=MO',
        )
