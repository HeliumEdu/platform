import datetime
from types import SimpleNamespace

from django.test import TestCase

from helium.common.utils.course_exception_helpers import get_course_exceptions, merge_exceptions, parse_csv_exceptions

JAN_10 = datetime.date(2026, 1, 10)
JAN_20 = datetime.date(2026, 1, 20)
FEB_5 = datetime.date(2026, 2, 5)
MAR_1 = datetime.date(2026, 3, 1)


class TestCaseParseCsvExceptions(TestCase):
    def test_parses_yyyymmdd_tokens_in_input_order(self):
        self.assertEqual(parse_csv_exceptions('20260205,20260110'), [FEB_5, JAN_10])

    def test_blank_input_yields_no_dates(self):
        for csv in ('', '   ', None):
            self.assertEqual(parse_csv_exceptions(csv), [], msg=repr(csv))

    def test_skips_malformed_tokens_and_keeps_valid_ones(self):
        self.assertEqual(parse_csv_exceptions('20260110,,2026-01-20,20261399,20260205'), [JAN_10, FEB_5])

    def test_does_not_deduplicate(self):
        self.assertEqual(parse_csv_exceptions('20260110,20260110'), [JAN_10, JAN_10])


class TestCaseMergeExceptions(TestCase):
    def test_returns_empty_list_when_both_inputs_are_empty(self):
        self.assertEqual(merge_exceptions([], []), [])

    def test_returns_course_exceptions_when_group_exceptions_are_empty(self):
        self.assertEqual(merge_exceptions([JAN_10, FEB_5], []), [JAN_10, FEB_5])

    def test_returns_group_exceptions_when_course_exceptions_are_empty(self):
        self.assertEqual(merge_exceptions([], [JAN_20, MAR_1]), [JAN_20, MAR_1])

    def test_combines_course_and_group_exceptions_without_overlap(self):
        self.assertEqual(merge_exceptions([JAN_10], [FEB_5]), [JAN_10, FEB_5])

    def test_deduplicates_dates_that_appear_in_both_lists(self):
        self.assertEqual(merge_exceptions([JAN_10, FEB_5], [FEB_5, MAR_1]), [JAN_10, FEB_5, MAR_1])

    def test_deduplicates_dates_repeated_within_one_list(self):
        self.assertEqual(merge_exceptions([FEB_5, FEB_5], []), [FEB_5])

    def test_returns_sorted_result_regardless_of_input_order(self):
        self.assertEqual(merge_exceptions([MAR_1, JAN_10], [FEB_5, JAN_20]), [JAN_10, JAN_20, FEB_5, MAR_1])

    def test_does_not_mutate_the_input_lists(self):
        course = [MAR_1, JAN_10]
        group = [FEB_5]

        merge_exceptions(course, group)

        self.assertEqual(course, [MAR_1, JAN_10])
        self.assertEqual(group, [FEB_5])


class TestCaseGetCourseExceptions(TestCase):
    def test_merges_course_and_group_csv_fields_into_one_deduplicated_set(self):
        course = SimpleNamespace(exceptions='20260301,20260205',
                                 course_group=SimpleNamespace(exceptions='20260205,20260110'))

        self.assertEqual(get_course_exceptions(course), {JAN_10, FEB_5, MAR_1})

    def test_empty_csv_on_either_side_is_tolerated(self):
        course = SimpleNamespace(exceptions='', course_group=SimpleNamespace(exceptions='20260110'))

        self.assertEqual(get_course_exceptions(course), {JAN_10})
