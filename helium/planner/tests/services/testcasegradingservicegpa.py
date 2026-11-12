import datetime
from decimal import Decimal

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.utils import gradeutils
from helium.planner.models import Course, CourseGroup
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper

_FOUR_POINT = gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_0)
_ONE_TO_FIVE_PASS_75 = gradeutils.preset_grade_scale(enums.GRADE_SCALE_1_5_PASS_75)


class TestCaseGradingServiceGpa(TestCase):
    def test_grade_point_at_band_edge_earns_that_band(self):
        # WHEN
        at_edge = gradingservice.grade_point_for(80, _FOUR_POINT)
        below_edge = gradingservice.grade_point_for(79.99, _FOUR_POINT)

        # THEN
        self.assertEqual(at_edge, 3.0)
        self.assertEqual(below_edge, 2.0)

    def test_grade_point_uses_the_grade_rounded_as_displayed(self):
        # WHEN
        rounds_up = gradingservice.grade_point_for(Decimal('89.9950'), _FOUR_POINT)
        rounds_down = gradingservice.grade_point_for(Decimal('89.9949'), _FOUR_POINT)

        # THEN
        self.assertEqual(rounds_up, 4.0)
        self.assertEqual(rounds_down, 3.0)

    def test_grade_point_above_100_earns_top_band(self):
        # WHEN
        grade_point = gradingservice.grade_point_for(104.5, _FOUR_POINT)

        # THEN
        self.assertEqual(grade_point, 4.0)

    def test_grade_point_of_ungraded_class(self):
        # WHEN
        grade_point = gradingservice.grade_point_for(-1, _FOUR_POINT)

        # THEN
        self.assertEqual(grade_point, -1)

    def test_grade_point_on_scale_where_lower_is_better(self):
        # WHEN
        top = gradingservice.grade_point_for(97, _ONE_TO_FIVE_PASS_75)
        passing = gradingservice.grade_point_for(75, _ONE_TO_FIVE_PASS_75)
        failing = gradingservice.grade_point_for(74.99, _ONE_TO_FIVE_PASS_75)

        # THEN
        self.assertEqual(top, 1.0)
        self.assertEqual(passing, 3.0)
        self.assertEqual(failing, 5.0)

    def test_every_preset_grade_point_falls_in_its_band(self):
        for template, preset in enums.GRADE_SCALE_TEMPLATES.items():
            with self.subTest(template=template):
                for band in preset['scale']:
                    # WHEN
                    grade_point = gradingservice.grade_point_for(band['min_grade'], preset['scale'])

                    # THEN
                    self.assertEqual(grade_point, band['grade_point'], f"{preset['label']} at {band['min_grade']}")

    def test_gpa_weighs_classes_by_credits(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('3'), Decimal('4')), (Decimal('1'), Decimal('2'))])

        # THEN
        self.assertEqual(gpa, 3.5)

    def test_gpa_leaves_out_classes_without_credits(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('3'), Decimal('4')), (Decimal('0'), Decimal('0'))])

        # THEN
        self.assertEqual(gpa, 4.0)

    def test_no_gpa_when_no_class_has_credits(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('0'), Decimal('4')), (Decimal('0'), Decimal('2'))])

        # THEN
        self.assertEqual(gpa, -1)

    def test_gpa_leaves_out_ungraded_classes(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('3'), Decimal('-1')), (Decimal('1'), Decimal('2'))])

        # THEN
        self.assertEqual(gpa, 2.0)

    def test_no_gpa_when_only_ungraded_classes_have_credits(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('3'), Decimal('-1')), (Decimal('0'), Decimal('4')),
                                      (Decimal('0'), Decimal('2'))])

        # THEN
        self.assertEqual(gpa, -1)

    def test_gpa_when_nothing_is_graded(self):
        # WHEN
        gpa = gradingservice.gpa_for([(Decimal('3'), Decimal('-1'))])

        # THEN
        self.assertEqual(gpa, -1)

    def test_grading_a_class_sets_its_grade_point_and_group_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        course1 = coursehelper.given_graded_course_exists(course_group, 85, credits=3)
        course2 = coursehelper.given_graded_course_exists(course_group, 72, credits=1)

        # THEN
        course1.refresh_from_db()
        course2.refresh_from_db()
        course_group.refresh_from_db()
        self.assertEqual(float(course1.grade_point), 3.0)
        self.assertEqual(float(course2.grade_point), 2.0)
        self.assertEqual(float(course_group.gpa), 2.75)

    def test_extra_credit_class_earns_top_band(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        course = coursehelper.given_graded_course_exists(course_group, 110, credits=3)

        # THEN
        course.refresh_from_db()
        self.assertAlmostEqual(float(course.current_grade), 110, places=4)
        self.assertEqual(float(course.grade_point), 4.0)

    def test_changing_credits_recalculates_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_graded_course_exists(course_group, 95, credits=1)
        coursehelper.given_graded_course_exists(course_group, 75, credits=1)

        # WHEN
        course1 = Course.objects.get(pk=course1.pk)
        course1.credits = 3
        course1.save()

        # THEN
        course_group.refresh_from_db()
        self.assertEqual(float(course_group.gpa), 3.5)

    def test_ungraded_group_has_no_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group, credits=3)

        # WHEN
        gradingservice.recalculate_course_grade(course.pk)
        gradingservice.recalculate_course_group_grade(course_group.pk)

        # THEN
        course.refresh_from_db()
        course_group.refresh_from_db()
        self.assertEqual(float(course.grade_point), -1)
        self.assertEqual(float(course_group.gpa), -1)

    def test_recalculate_course_group_gpa_uses_the_current_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)
        CourseGroup.objects.filter(pk=course_group.pk).update(
            grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_5))

        # WHEN
        gradingservice.recalculate_course_group_gpa(course_group.pk)

        # THEN
        course.refresh_from_db()
        course_group.refresh_from_db()
        self.assertEqual(float(course.grade_point), 4.5)
        self.assertEqual(float(course_group.gpa), 4.5)

    def test_group_without_a_scale_has_no_grade_points_or_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user, grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)

        # THEN
        course.refresh_from_db()
        course_group.refresh_from_db()
        self.assertEqual(float(course.grade_point), -1)
        self.assertEqual(float(course_group.gpa), -1)

    def test_cumulative_pools_by_the_latest_group_with_a_scale(self):
        # GIVEN
        us_4 = gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_0)
        course_groups = [
            {'id': 1, 'start_date': datetime.date(2024, 1, 1), 'example_schedule': False, 'grade_scale': us_4},
            {'id': 2, 'start_date': datetime.date(2025, 1, 1), 'example_schedule': False, 'grade_scale': us_4},
            {'id': 3, 'start_date': datetime.date(2026, 1, 1), 'example_schedule': False, 'grade_scale': []},
            {'id': 4, 'start_date': datetime.date(2026, 6, 1), 'example_schedule': True, 'grade_scale': _ONE_TO_FIVE_PASS_75},
        ]

        # WHEN
        ids = gradingservice.cumulative_gpa_course_group_ids(course_groups)

        # THEN
        self.assertEqual(ids, [1, 2])

    def test_no_cumulative_when_no_group_has_a_scale(self):
        # GIVEN
        course_groups = [
            {'id': 1, 'start_date': datetime.date(2025, 1, 1), 'example_schedule': False, 'grade_scale': []},
        ]

        # WHEN
        ids = gradingservice.cumulative_gpa_course_group_ids(course_groups)

        # THEN
        self.assertEqual(ids, [])
