import datetime

import pytz
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseGradingService(TestCase):
    def test_trend_positive(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                             current_grade='0/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                             current_grade='200/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                             current_grade='400/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category.pk)
        self.assertEqual(float(course_group.trend), 1)
        self.assertEqual(float(course.trend), 1)
        self.assertEqual(float(category.trend), 1)

    def test_trend_negative(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                             current_grade='400/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                             current_grade='200/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                             current_grade='0/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category.pk)
        self.assertEqual(float(course_group.trend), -1)
        self.assertEqual(float(course.trend), -1)
        self.assertEqual(float(category.trend), -1)

    def test_unweighted_grade_unchanged(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category, current_grade='-1/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category.pk)
        self.assertEqual(course_group.average_grade, -1)
        self.assertEqual(course.current_grade, -1)
        self.assertEqual(category.average_grade, -1)

    def test_unweighted_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course_group_ungraded = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        course_ungraded = coursehelper.given_course_exists(course_group_ungraded)
        category1 = categoryhelper.given_category_exists(course1)
        category2 = categoryhelper.given_category_exists(course2)
        category_ungraded = categoryhelper.given_category_exists(course_ungraded)

        # WHEN
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='100/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course_group_ungraded = CourseGroup.objects.get(pk=course_group_ungraded.pk)
        course1 = Course.objects.get(pk=course1.pk)
        course2 = Course.objects.get(pk=course2.pk)
        course_ungraded = Course.objects.get(pk=course_ungraded.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        category_ungraded = Category.objects.get(pk=category_ungraded.pk)
        self.assertEqual(float(course_group.average_grade), 100)
        self.assertEqual(course_group_ungraded.average_grade, -1)
        self.assertEqual(course1.current_grade, 100)
        self.assertEqual(course2.current_grade, -1)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 100)
        self.assertEqual(category2.average_grade, -1)
        self.assertEqual(category_ungraded.average_grade, -1)

        # WHEN
        homeworkhelper.given_homework_exists(course2, category=category2, completed=True, current_grade='50/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course_group_ungraded = CourseGroup.objects.get(pk=course_group_ungraded.pk)
        course1 = Course.objects.get(pk=course1.pk)
        course2 = Course.objects.get(pk=course2.pk)
        course_ungraded = Course.objects.get(pk=course_ungraded.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        category_ungraded = Category.objects.get(pk=category_ungraded.pk)
        self.assertEqual(float(course_group.average_grade), 75)
        self.assertEqual(course_group_ungraded.average_grade, -1)
        self.assertEqual(course1.current_grade, 100)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 100)
        self.assertEqual(category2.average_grade, 50)
        self.assertEqual(category_ungraded.average_grade, -1)

        # WHEN
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True, current_grade='80/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course1 = Course.objects.get(pk=course1.pk)
        course2 = Course.objects.get(pk=course2.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        self.assertEqual(float(course_group.average_grade), 70)
        self.assertEqual(course1.current_grade, 90)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(float(category1.average_grade), 90)
        self.assertEqual(category2.average_grade, 50)

        # WHEN
        homework1.delete()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course_group_ungraded = CourseGroup.objects.get(pk=course_group_ungraded.pk)
        course1 = Course.objects.get(pk=course1.pk)
        course2 = Course.objects.get(pk=course2.pk)
        course_ungraded = Course.objects.get(pk=course_ungraded.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        category_ungraded = Category.objects.get(pk=category_ungraded.pk)
        self.assertEqual(float(course_group.average_grade), 65)
        self.assertEqual(course_group_ungraded.average_grade, -1)
        self.assertEqual(course1.current_grade, 80)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 80)
        self.assertEqual(category2.average_grade, 50)
        self.assertEqual(category_ungraded.average_grade, -1)

    def test_weighted_grade_imbalanced(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        category2 = categoryhelper.given_category_exists(course)
        category3 = categoryhelper.given_category_exists(course)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='10/10')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='50/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='40/50')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='60/100')
        homeworkhelper.given_homework_exists(course, category=category3, completed=True, current_grade='200/200')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        category3 = Category.objects.get(pk=category3.pk)
        # 360/460 total points
        self.assertEqual(float(course_group.average_grade), 78.2609)
        self.assertEqual(float(course.current_grade), 78.2609)
        # 60/110 total points
        self.assertEqual(float(category1.average_grade), 54.5455)
        # 100/150 total points
        self.assertEqual(float(category2.average_grade), 66.6667)
        # 200/200 total points
        self.assertEqual(float(category3.average_grade), 100)

    def test_incomplete_not_graded(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        categoryhelper.given_category_exists(course)

        # WHEN
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, current_grade='50/100')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='100/100')

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category1.pk)
        self.assertEqual(float(course_group.average_grade), 100)
        self.assertEqual(float(course.current_grade), 100)
        self.assertEqual(float(category.average_grade), 100)

        # WHEN
        homework1.completed = True
        homework1.save()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category1.pk)
        self.assertEqual(float(course_group.average_grade), 75)
        self.assertEqual(float(course.current_grade), 75)
        self.assertEqual(float(category.average_grade), 75)

        # WHEN
        homework1.completed = False
        homework1.save()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        course = Course.objects.get(pk=course.pk)
        category = Category.objects.get(pk=category1.pk)
        self.assertEqual(float(course_group.average_grade), 100)
        self.assertEqual(float(course.current_grade), 100)
        self.assertEqual(float(category.average_grade), 100)

        # TODO: course non weight examples
        # (25 + 75) / 2

        # (25 + 75 + 25 + 75) / 4

        # (25 + 75 + 25 + 75 + 100) / 5

        # (25 + 75 + 25 + 75 + 100 + 25 + 25) / 7

        # (80 + 90 + 25 + 75 + 100 + 25 + 25) / 7

        # (80 + 90 + 80 + 90 + 100 + 25 + 25) / 7

        # (80 + 90 + 100 + 25 + 25) / 5

        # TODO: course weighted examples
        # (((.5 * .3) + (0 * .6) + (0 * .1)) / .3) * 100

        # (((.5 * .3) + (.35 * .6) + (0 * .1)) / .9) * 100

        # ((.5 * .3) + (.35 * .6) + (.9 * .1)) * 100

        # ((.5625 * .3) + (.6 * .6) + (.675 * .1)) * 100

        # ((.5625 * .3) + (.825 * .6) + (.85 * .1)) * 100

        # ((.75 * .3) + (.825 * .6) + (.85 * .1)) * 100

        # TODO: course differing grade bases
        # Grade of 10/10 (100%)

        # Grade of 50/100 (50%)

        # Grade of 40/50 (100%)

        # Grade of 60/100 (50%)

        # Grade of 200/200 (100%)

        # This course has a total of 110 points (60.303030303030305)

        # TODO: course non weight grade points examples
        # ((25 * 30)) / 30

        # ((25 * 30) + (75 * 50)) / 80

        # ((25 * 30) + (75 * 50) + (50 * 20)) / 100

        # TODO: course weighted grade points examples
        # (25) / 1

        # (25 + 75) / 2

        # (25 + 75 + 50) / 3

        # TODO: tests for course grade point series
