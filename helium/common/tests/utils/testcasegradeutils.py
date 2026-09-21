from django.test import SimpleTestCase

from helium.common.utils.gradeutils import at_risk_threshold_for_time_zone


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
