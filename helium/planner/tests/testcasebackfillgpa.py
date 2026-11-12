import importlib

from django.apps import apps
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Course, CourseGroup
from helium.planner.tests.helpers import coursegrouphelper, coursehelper

migration = importlib.import_module('helium.planner.migrations.0081_gpa')


class TestCaseBackfillGpa(TestCase):
    def test_example_schedule_groups_get_the_4_0_scale_and_gpa_from_stored_grades(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user, example_schedule=True)
        graded = coursehelper.given_course_exists(course_group, credits=3)
        ungraded = coursehelper.given_course_exists(course_group, credits=3)
        Course.objects.filter(pk=graded.pk).update(current_grade=96.25)
        CourseGroup.objects.filter(pk=course_group.pk).update(grade_scale=[],
                                                              grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        migration.backfill_gpa(apps, None)

        # THEN
        course_group.refresh_from_db()
        graded.refresh_from_db()
        ungraded.refresh_from_db()
        self.assertEqual(course_group.grade_scale_template, enums.GRADE_SCALE_4_0)
        self.assertEqual(course_group.grade_scale, enums.GRADE_SCALE_TEMPLATES[enums.GRADE_SCALE_4_0]['scale'])
        self.assertEqual(float(graded.grade_point), 4.0)
        self.assertEqual(float(ungraded.grade_point), -1)
        self.assertEqual(float(course_group.gpa), 4.0)

    def test_other_groups_keep_no_grade_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        graded = coursehelper.given_course_exists(course_group, credits=3)
        Course.objects.filter(pk=graded.pk).update(current_grade=96.25)
        CourseGroup.objects.filter(pk=course_group.pk).update(grade_scale=[],
                                                              grade_scale_template=enums.GRADE_SCALE_NONE)

        # WHEN
        migration.backfill_gpa(apps, None)

        # THEN
        course_group.refresh_from_db()
        graded.refresh_from_db()
        self.assertEqual(course_group.grade_scale_template, enums.GRADE_SCALE_NONE)
        self.assertEqual(course_group.grade_scale, [])
        self.assertEqual(float(graded.grade_point), -1)
        self.assertEqual(float(course_group.gpa), -1)
