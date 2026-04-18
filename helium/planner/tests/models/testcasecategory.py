__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.core.exceptions import ValidationError
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper


class TestCaseCategory(TestCase):
    def test_weight_exceeding_course_total_fails_clean(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, weight=50)
        categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)

        # WHEN
        category = categoryhelper.given_category_exists(course, title='Test Category 3', weight=0)
        category.weight = 1

        # THEN
        with self.assertRaises(ValidationError) as ctx:
            category.full_clean()
        self.assertIn('weight', ctx.exception.message_dict)

    def test_weight_exactly_100_passes_clean(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, weight=50)

        # WHEN
        category = categoryhelper.given_category_exists(course, title='Test Category 2', weight=0)
        category.weight = 50

        # THEN
        category.full_clean()


