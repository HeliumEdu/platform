from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.utils import gradeutils
from helium.planner.models import Course, CourseGroup
from helium.planner.tests.helpers import coursegrouphelper, coursehelper


class TestCaseCourseGroup(TestCase):
    def test_saving_a_preset_scale_derives_its_template_and_recalculates_gpa(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)

        # WHEN
        course_group.grade_scale = gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_5)
        course_group.save()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        self.assertEqual(course_group.grade_scale_template, enums.GRADE_SCALE_4_5)
        self.assertEqual(float(course_group.gpa), 4.5)
        self.assertEqual(float(Course.objects.get(pk=course.pk).grade_point), 4.5)

    def test_saving_a_custom_scale_clears_its_template(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_graded_course_exists(course_group, 96, credits=3)

        # WHEN
        course_group.grade_scale = [
            {'min_grade': 0, 'grade_point': 0, 'label': 'Fail'},
            {'min_grade': 50, 'grade_point': 2, 'label': 'Pass'},
            {'min_grade': 80, 'grade_point': 3, 'label': 'Merit'},
        ]
        course_group.save()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        self.assertIsNone(course_group.grade_scale_template)
        self.assertEqual(float(course_group.gpa), 3)
        self.assertEqual(float(Course.objects.get(pk=course.pk).grade_point), 3)
