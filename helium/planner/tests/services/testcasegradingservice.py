import datetime

import pytz
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup, Course, Category
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"


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
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2')
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3')

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
        self.assertEqual(float(category1.average_grade), 54.5454)
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
        categoryhelper.given_category_exists(course, title='Test Category 2')

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

    def test_unweighted_course_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2')

        # WHEN
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='25/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         current_grade='25/100')
        homework4 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         current_grade='75/100')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='100/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (25 + 75 + 25 + 75 + 100) / 5
        self.assertEqual(float(course.current_grade), 60)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='25/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='25/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (25 + 75 + 25 + 75 + 100 + 25 + 25) / 7
        self.assertEqual(float(course.current_grade), 50)

        # WHEN
        homework1.current_grade = '80/100'
        homework1.save()
        homework2.current_grade = '90/100'
        homework2.save()

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (80 + 90 + 25 + 75 + 100 + 25 + 25) / 7
        self.assertEqual(float(course.current_grade), 60)

        # WHEN
        homework3.current_grade = '80/100'
        homework3.save()
        homework4.current_grade = '90/100'
        homework4.save()

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (80 + 90 + 80 + 90 + 100 + 25 + 25) / 7
        self.assertEqual(float(course.current_grade), 70)

        # WHEN
        homework3.delete()
        homework4.delete()

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (80 + 90 + 100 + 25 + 25) / 5
        self.assertEqual(float(course.current_grade), 64)

    def test_weighted_course_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=60)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=10)

        # WHEN
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='25/100')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='50/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (((.5 * .3) + (0 * .6) + (0 * .1)) / .3) * 100
        self.assertEqual(float(course.current_grade), 50)

        # WHEN
        homework4 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         current_grade='35/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # (((.5 * .3) + (.35 * .6) + (0 * .1)) / .9) * 100
        self.assertEqual(float(course.current_grade), 40)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category3, completed=True, current_grade='90/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # ((.5 * .3) + (.35 * .6) + (.9 * .1)) * 100
        self.assertEqual(float(course.current_grade), 45)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='75/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='85/100')
        homework8 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         current_grade='45/100')

        # THEN
        course = Course.objects.get(pk=course.pk)
        # ((.5625 * .3) + (.6 * .6) + (.675 * .1)) * 100
        self.assertEqual(float(course.current_grade), 59.6250)

        # WHEN
        homework4.current_grade = '80/100'
        homework4.save()
        homework8.current_grade = '80/100'
        homework8.save()

        # THEN
        course = Course.objects.get(pk=course.pk)
        # ((.5625 * .3) + (.825 * .6) + (.85 * .1)) * 100
        self.assertEqual(float(course.current_grade), 74.875)

        # WHEN
        homework1.delete()
        homework3.delete()

        # THEN
        course = Course.objects.get(pk=course.pk)
        # ((.75 * .3) + (.825 * .6) + (.85 * .1)) * 100
        self.assertEqual(float(course.current_grade), 80.5)

    def test_unweight_graded_points(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2')
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3')
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='25/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='50/100')
        homework4 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='60/80')
        homework5 = homeworkhelper.given_homework_exists(course, category=category3,
                                                         start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=pytz.utc),
                                                         completed=True, current_grade='4/5')
        # Incomplete homework are not graded
        homeworkhelper.given_homework_exists(course, category=category1,
                                             start=datetime.datetime(2017, 4, 8, 21, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 21, 30, tzinfo=pytz.utc),
                                             current_grade='80/100')

        # WHEN
        grade_points = gradingservice.get_grade_points_for_course(course.pk)

        # THEN
        self.assertEqual(len(grade_points), 5)
        # (25) / 1
        self.assertEqual(grade_points[0], [homework1.start, 25])
        # (25 + 75) / 2
        self.assertEqual(grade_points[1], [homework2.start, 50])
        # (25 + 75 + 50) / 3
        self.assertEqual(grade_points[2], [homework3.start, 50])
        # (25 + 75 + 50 + (60/80)) / 4
        self.assertEqual(grade_points[3], [homework4.start, 55.2632])
        # (25 + 75 + 50 + (60/80) + (4/5)) / 5
        self.assertEqual(grade_points[4], [homework5.start, 55.5844])

    def test_weight_graded_points(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=20)
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='25/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='50/100')
        homework4 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=pytz.utc),
                                                         current_grade='60/80')
        homework5 = homeworkhelper.given_homework_exists(course, category=category3,
                                                         start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=pytz.utc),
                                                         end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=pytz.utc),
                                                         completed=True, current_grade='4/5')
        # Incomplete homework are not graded
        homeworkhelper.given_homework_exists(course, category=category1,
                                             start=datetime.datetime(2017, 4, 8, 21, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 21, 30, tzinfo=pytz.utc),
                                             current_grade='80/100')

        # WHEN
        grade_points = gradingservice.get_grade_points_for_course(course.pk)

        # THEN
        self.assertEqual(len(grade_points), 5)
        # ((25 * 30)) / 30
        self.assertEqual(grade_points[0], [homework1.start, 25])
        # ((25 * 30) + (75 * 50)) / 80
        self.assertEqual(grade_points[1], [homework2.start, 56.25])
        # ((25 * 30) + (75 * 50) + (50 * 20)) / 100
        self.assertEqual(grade_points[2], [homework3.start, 55])
        # ((25 * 30) + (75 * 50) + (50 * 20) + ((60/80) * 30)) / 100
        self.assertEqual(grade_points[3], [homework4.start, 59.6154])
        # ((25 * 30) + (75 * 50) + (50 * 20) + ((60/80) * 30) + ((4/5) * 10)) / 100
        self.assertEqual(grade_points[4], [homework5.start, 62.3333])

    def test_category_changed_deleted_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=20)
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                             current_grade='25/60')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                             current_grade='75/80')
        homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                             current_grade='50/120')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=pytz.utc),
                                             current_grade='60/80')
        homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=pytz.utc),
                                             current_grade='110/130')
        course = Course.objects.get(pk=course.pk)
        category1 = Category.objects.get(pk=category1.pk)
        self.assertEqual(float(course.current_grade), 77.8893)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 18.2143)

        # WHEN
        category2.weight = 30
        category2.save()
        category1.weight = 50
        category1.save()

        # THEN
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 30.3571)
        self.assertEqual(float(category2.average_grade), 93.75)
        self.assertEqual(float(category2.grade_by_weight), 28.125)

        # WHEN
        category2.delete()

        # THEN
        course = Course.objects.get(pk=course.pk)
        category1 = Category.objects.get(pk=category1.pk)
        self.assertEqual(float(course.current_grade), 61.6531)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 30.3571)



    def test_course_deleted_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course1, weight=30)
        category2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course2, title='Test Category 3', weight=20)
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=pytz.utc),
                                             current_grade='25/100')
        homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=pytz.utc),
                                             current_grade='75/100')
        homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=pytz.utc),
                                             current_grade='50/100')
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=pytz.utc),
                                             current_grade='60/80')
        homeworkhelper.given_homework_exists(course2, category=category3,
                                             start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=pytz.utc),
                                             end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=pytz.utc),
                                             completed=True, current_grade='4/5')
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        self.assertEqual(float(course_group.average_grade), 58.006)

        # WHEN
        course2.delete()

        # THEN
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        self.assertEqual(float(course_group.average_grade), 64.5833)
