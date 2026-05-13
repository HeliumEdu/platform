__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.exceptions import ValidationError
from django.test import TestCase

from helium.common.utils.validators import validate_fraction, validate_quill_delta


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
