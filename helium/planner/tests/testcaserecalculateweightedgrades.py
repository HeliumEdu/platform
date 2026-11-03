import importlib

from django.apps import apps
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Course, CourseGroup
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper, homeworkhelper

migration = importlib.import_module('helium.planner.migrations.0076_recalculate_weighted_grades')


class TestCaseRecalculateWeightedGrades(TestCase):
    def test_restores_stale_weighted_grades_to_the_pooled_category_formula(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        quizzes = categoryhelper.given_category_exists(course, title='Quizzes', weight=50)
        exams = categoryhelper.given_category_exists(course, title='Exams', weight=50)
        homeworkhelper.given_homework_exists(course, category=quizzes, completed=True, current_grade='25/30')
        homeworkhelper.given_homework_exists(course, category=quizzes, completed=True, current_grade='90/100')
        homeworkhelper.given_homework_exists(course, category=exams, completed=True, current_grade='50/100')
        Course.objects.filter(pk=course.pk).update(current_grade=12.34)
        CourseGroup.objects.filter(pk=course_group.pk).update(overall_grade=12.34)

        # WHEN
        migration.recalculate_weighted_grades(apps, None)

        # THEN
        course.refresh_from_db()
        course_group.refresh_from_db()
        self.assertAlmostEqual(float(course.current_grade), 69.2308, places=4)
        self.assertAlmostEqual(float(course_group.overall_grade), 69.2308, places=4)

    def test_leaves_points_based_classes_alone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course, weight=0)
        homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade='25/30')
        Course.objects.filter(pk=course.pk).update(current_grade=12.34)

        # WHEN
        migration.recalculate_weighted_grades(apps, None)

        # THEN
        course.refresh_from_db()
        self.assertAlmostEqual(float(course.current_grade), 12.34, places=4)
