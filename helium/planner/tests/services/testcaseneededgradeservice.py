from django.test import TestCase

from helium.planner.services import neededgradeservice
from helium.planner.services.neededgradeservice import ABOVE_TARGET, ACHIEVABLE, INVALID_TOTAL_WEIGHT, \
    TARGET_CATEGORY_HAS_NO_WEIGHT, UNACHIEVABLE


def _category(category_id, weight, grade):
    return {'id': category_id, 'weight': weight, 'overall_grade': grade}


class TestCaseNeededGradeService(TestCase):
    def test_needed_assignment_score_from_total_points(self):
        # WHEN
        result = neededgradeservice.calculate_needed_assignment_score(60.0, 110.0, 100, 70)

        # THEN
        self.assertEqual(ACHIEVABLE, result['state'])
        self.assertAlmostEqual(87, result['needed_grade'], places=4, msg='(0.7 × 210 − 60) / 100 = 87%')

    def test_needed_assignment_score_already_exceeded(self):
        # WHEN
        result = neededgradeservice.calculate_needed_assignment_score(60.0, 110.0, 100, 20)

        # THEN
        self.assertEqual(ABOVE_TARGET, result['state'])

    def test_needed_assignment_score_more_than_full_marks(self):
        # WHEN
        result = neededgradeservice.calculate_needed_assignment_score(60.0, 110.0, 100, 90)

        # THEN
        self.assertEqual(UNACHIEVABLE, result['state'])
        self.assertAlmostEqual(129, result['needed_grade'], places=4)

    def test_needed_assignment_score_weighs_the_assignment_by_its_points(self):
        # WHEN
        result = neededgradeservice.calculate_needed_assignment_score(60.0, 110.0, 10, 60)

        # THEN
        self.assertEqual(UNACHIEVABLE, result['state'],
                         'a 10-point assignment can lift 60/110 to at most 70/120 = 58.3%')

    def test_to_assignment_score_converts_a_category_average(self):
        # GIVEN
        category_need = {'needed_grade': 85, 'state': ACHIEVABLE}

        # WHEN
        result = neededgradeservice.to_assignment_score(category_need, 40, 50, 100)

        # THEN
        self.assertEqual(ACHIEVABLE, result['state'])
        self.assertAlmostEqual(87.5, result['needed_grade'], places=4,
                               msg='(0.85 × 150 − 40) / 100 = 87.5% on the remaining assignment')

    def test_to_assignment_score_matches_the_average_with_nothing_graded(self):
        # GIVEN
        category_need = {'needed_grade': 72, 'state': ACHIEVABLE}

        # WHEN
        result = neededgradeservice.to_assignment_score(category_need, 0, 0, 100)

        # THEN
        self.assertAlmostEqual(72, result['needed_grade'], places=4)

    def test_to_assignment_score_passes_weight_errors_through(self):
        # GIVEN
        category_need = {'needed_grade': 0, 'state': INVALID_TOTAL_WEIGHT}

        # WHEN
        result = neededgradeservice.to_assignment_score(category_need, 40, 50, 100)

        # THEN
        self.assertEqual(INVALID_TOTAL_WEIGHT, result['state'])

    def test_needed_grade_basic(self):
        # GIVEN
        categories = [_category(1, 30, 80), _category(2, 40, 90), _category(3, 30, -1)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 3, 85)

        # THEN
        self.assertEqual(ACHIEVABLE, result['state'])
        self.assertAlmostEqual(83.33, result['needed_grade'], places=2)

    def test_needed_grade_treats_averages_at_or_below_one_percent_as_percentages(self):
        # GIVEN
        categories = [_category(1, 30, 0.8), _category(2, 40, 0.9), _category(3, 30, -1)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 3, 85)

        # THEN
        self.assertEqual(UNACHIEVABLE, result['state'],
                         'averages of 0.8% and 0.9% leave (8500 - 24 - 36) / 30 = 281.33% needed')
        self.assertAlmostEqual(281.33, result['needed_grade'], places=2)

    def test_needed_grade_already_above_target(self):
        # GIVEN
        categories = [_category(1, 70, 95), _category(2, 30, -1)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 2, 60)

        # THEN
        self.assertEqual(ABOVE_TARGET, result['state'])
        self.assertLess(result['needed_grade'], 0)

    def test_needed_grade_unachievable(self):
        # GIVEN
        categories = [_category(1, 60, 70), _category(2, 40, -1)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 2, 95)

        # THEN
        self.assertEqual(UNACHIEVABLE, result['state'])
        self.assertGreater(result['needed_grade'], 100)

    def test_needed_grade_boundaries(self):
        # WHEN
        exactly_full = neededgradeservice.calculate_needed_grade([_category(1, 50, 80), _category(2, 50, -1)], 2, 90)
        exactly_none = neededgradeservice.calculate_needed_grade([_category(1, 70, 100), _category(2, 30, -1)], 2, 70)

        # THEN
        self.assertEqual(ACHIEVABLE, exactly_full['state'])
        self.assertAlmostEqual(100, exactly_full['needed_grade'], places=2)
        self.assertEqual(ACHIEVABLE, exactly_none['state'])
        self.assertAlmostEqual(0, exactly_none['needed_grade'], places=2)

    def test_needed_grade_counts_other_ungraded_categories_as_zero(self):
        # GIVEN
        categories = [_category(1, 30, 80), _category(2, 40, -1), _category(3, 30, -1)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 3, 85)

        # THEN
        self.assertEqual(UNACHIEVABLE, result['state'])

    def test_needed_grade_ignores_the_targets_current_average(self):
        # GIVEN
        categories = [_category(1, 40, 85), _category(2, 30, 90), _category(3, 30, 88)]

        # WHEN
        result = neededgradeservice.calculate_needed_grade(categories, 3, 90)

        # THEN
        self.assertEqual(ACHIEVABLE, result['state'])
        self.assertAlmostEqual(96.67, result['needed_grade'], places=2)

    def test_needed_grade_validates_its_inputs(self):
        # WHEN
        with self.assertRaises(ValueError):
            neededgradeservice.calculate_needed_grade([_category(1, 50, 80)], 999, 85)
        no_weight = neededgradeservice.calculate_needed_grade([_category(1, 100, 80), _category(2, 0, -1)], 2, 85)
        short_weights = neededgradeservice.calculate_needed_grade([_category(1, 40, 80), _category(2, 40, -1)], 2,
                                                                  85)
        rounded_weights = neededgradeservice.calculate_needed_grade(
            [_category(1, 33.33, 80), _category(2, 33.34, 90), _category(3, 33.33, -1)], 3, 85)

        # THEN
        self.assertEqual(TARGET_CATEGORY_HAS_NO_WEIGHT, no_weight['state'])
        self.assertEqual(INVALID_TOTAL_WEIGHT, short_weights['state'])
        self.assertAlmostEqual(80, short_weights['total_weight_accounted_for'])
        self.assertEqual(ACHIEVABLE, rounded_weights['state'])
