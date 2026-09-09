import datetime

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Homework
from helium.planner.tests.helpers import categoryhelper, coursegrouphelper, coursehelper


class TestCaseHomework(TestCase):
    def given_a_course(self):
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        return coursehelper.given_course_exists(course_group)

    def test_saving_with_a_category_does_not_load_it(self):
        # GIVEN
        course = self.given_a_course()
        category = categoryhelper.given_category_exists(course)
        homework = Homework(title='🧪 Test', all_day=False, show_end_time=False,
                            start=timezone.now(), end=timezone.now() + datetime.timedelta(hours=1),
                            priority=50, category_id=category.pk, course_id=course.pk)

        # WHEN
        homework.save()

        # THEN
        self.assertNotIn('category', homework._state.fields_cache)

    def test_saving_without_a_category_assigns_uncategorized(self):
        # GIVEN
        course = self.given_a_course()
        homework = Homework(title='🧪 Test', all_day=False, show_end_time=False,
                            start=timezone.now(), end=timezone.now() + datetime.timedelta(hours=1),
                            priority=50, course_id=course.pk)

        # WHEN
        homework.save()

        # THEN
        homework.refresh_from_db()
        self.assertEqual(homework.category.title, 'Uncategorized')
