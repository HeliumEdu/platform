__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.exceptions import ValidationError
from django.test import TestCase

from helium.common.utils.validators import validate_fraction


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
