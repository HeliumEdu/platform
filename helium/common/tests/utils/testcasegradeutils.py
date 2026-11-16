from django.test import SimpleTestCase

from helium.common import enums
from helium.common.utils.gradeutils import at_risk_threshold_for_time_zone, compatible_presets, \
    effective_grade_scale, format_grade_percent, is_compatible_preset, preset_grade_scale


class TestCaseGradeUtils(SimpleTestCase):
    def test_at_risk_threshold_is_50_where_pass_is_40_or_below(self):
        # WHEN
        threshold = at_risk_threshold_for_time_zone('Europe/London')

        # THEN
        self.assertEqual(threshold, 50)

    def test_at_risk_threshold_is_60_where_pass_is_around_50(self):
        # WHEN
        threshold = at_risk_threshold_for_time_zone('Australia/Sydney')

        # THEN
        self.assertEqual(threshold, 60)

    def test_at_risk_threshold_is_none_for_unlisted_time_zone(self):
        # WHEN
        threshold = at_risk_threshold_for_time_zone('Europe/Stockholm')

        # THEN
        self.assertIsNone(threshold)

    def test_whole_letter_preset_fits_plus_minus_groups(self):
        # WHEN
        on_plus_minus = compatible_presets(preset_grade_scale(enums.GRADE_SCALE_4_0_PLUS_MINUS))
        on_4_33 = compatible_presets(preset_grade_scale(enums.GRADE_SCALE_4_33_PLUS_MINUS))

        # THEN
        self.assertEqual(on_plus_minus, [enums.GRADE_SCALE_4_0, enums.GRADE_SCALE_4_0_PLUS_MINUS])
        self.assertEqual(on_4_33, [enums.GRADE_SCALE_4_0, enums.GRADE_SCALE_4_33_PLUS_MINUS])

    def test_preset_awarding_grades_the_group_does_not_is_incompatible(self):
        # WHEN
        plus_minus_on_whole_letter = is_compatible_preset(enums.GRADE_SCALE_4_0_PLUS_MINUS,
                                                          preset_grade_scale(enums.GRADE_SCALE_4_0))
        same_points_other_labels = is_compatible_preset(enums.GRADE_SCALE_4_0, preset_grade_scale(enums.GRADE_SCALE_9_0))

        # THEN
        self.assertFalse(plus_minus_on_whole_letter, 'a whole-letter school records no A-')
        self.assertFalse(same_points_other_labels, 'a 4 is an A on 4.0 but a B- on 9.0')

    def test_every_preset_fits_its_own_scale(self):
        for template, preset in enums.GRADE_SCALE_TEMPLATES.items():
            if template == enums.GRADE_SCALE_NONE:
                continue
            with self.subTest(template=template):
                # WHEN
                compatible = is_compatible_preset(template, preset['scale'])

                # THEN
                self.assertTrue(compatible)

    def test_no_preset_fits_a_group_without_a_scale(self):
        # WHEN
        compatible = compatible_presets([])

        # THEN
        self.assertEqual(compatible, [])

    def test_effective_grade_scale_is_the_presets_when_set(self):
        # GIVEN
        group_scale = preset_grade_scale(enums.GRADE_SCALE_4_0_PLUS_MINUS)

        # WHEN
        with_preset = effective_grade_scale(enums.GRADE_SCALE_4_0, group_scale)
        without = effective_grade_scale(None, group_scale)

        # THEN
        self.assertEqual(with_preset, preset_grade_scale(enums.GRADE_SCALE_4_0))
        self.assertEqual(without, group_scale)

    def test_effective_grade_scale_is_none_when_the_group_has_none(self):
        # WHEN
        scale = effective_grade_scale(enums.GRADE_SCALE_4_0, [])

        # THEN
        self.assertEqual(scale, [])

    def test_format_grade_percent_rounds_half_up_to_two_decimals(self):
        # WHEN
        thirds = format_grade_percent('2/3', enums.POINT)
        half = format_grade_percent('90.125/100', enums.POINT)

        # THEN
        self.assertEqual(thirds, '66.67%')
        self.assertEqual(half, '90.13%')

    def test_format_grade_percent_uses_the_comma_number_format(self):
        # WHEN
        grade = format_grade_percent('1234.5/100', enums.COMMA)

        # THEN
        self.assertEqual(grade, '1.234,50%')

    def test_format_grade_percent_groups_thousands_with_the_point_number_format(self):
        # WHEN
        grade = format_grade_percent('1234.5/100', enums.POINT)

        # THEN
        self.assertEqual(grade, '1,234.50%')

    def test_format_grade_percent_is_empty_when_ungraded(self):
        for grade in (enums.UNGRADED, ''):
            with self.subTest(grade=grade):
                # WHEN
                formatted = format_grade_percent(grade, enums.POINT)

                # THEN
                self.assertEqual(formatted, '')
