__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Homework
from helium.planner.services import gradingservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper


class TestCaseGradingService(TestCase):
    def test_trend_positive(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='0/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='200/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='400/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category.refresh_from_db()
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
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='400/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='200/100')
        homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='0/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category.refresh_from_db()
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
        course_group.refresh_from_db()
        course.refresh_from_db()
        category.refresh_from_db()
        self.assertEqual(course_group.overall_grade, -1)
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
        course_group.refresh_from_db()
        course_group_ungraded.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        course_ungraded.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        category_ungraded.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 100)
        self.assertEqual(course_group_ungraded.overall_grade, -1)
        self.assertEqual(course1.current_grade, 100)
        self.assertEqual(course2.current_grade, -1)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 100)
        self.assertEqual(category2.average_grade, -1)
        self.assertEqual(category_ungraded.average_grade, -1)

        # WHEN
        homeworkhelper.given_homework_exists(course2, category=category2, completed=True, current_grade='50/100')

        # THEN
        course_group.refresh_from_db()
        course_group_ungraded.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        course_ungraded.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        category_ungraded.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 75)
        self.assertEqual(course_group_ungraded.overall_grade, -1)
        self.assertEqual(course1.current_grade, 100)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 100)
        self.assertEqual(category2.average_grade, 50)
        self.assertEqual(category_ungraded.average_grade, -1)

        # WHEN
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True, current_grade='80/100')

        # THEN
        course_group.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 70)
        self.assertEqual(course1.current_grade, 90)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(float(category1.average_grade), 90)
        self.assertEqual(category2.average_grade, 50)

        # WHEN
        homework1.delete()

        # THEN
        course_group.refresh_from_db()
        course_group_ungraded.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        course_ungraded.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        category_ungraded.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 65)
        self.assertEqual(course_group_ungraded.overall_grade, -1)
        self.assertEqual(course1.current_grade, 80)
        self.assertEqual(course2.current_grade, 50)
        self.assertEqual(course_ungraded.current_grade, -1)
        self.assertEqual(float(category1.average_grade), 80)
        self.assertEqual(category2.average_grade, 50)
        self.assertEqual(category_ungraded.average_grade, -1)

    def test_unweighted_grade_imbalanced(self):
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
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        category3.refresh_from_db()
        # 360/460 total points
        self.assertEqual(float(course_group.overall_grade), 78.2609)
        self.assertEqual(float(course.current_grade), 78.2609)
        # 60/110 total points
        self.assertEqual(float(category1.average_grade), 54.5454)
        # 100/150 total points
        self.assertEqual(float(category2.average_grade), 66.6667)
        # 200/200 total points
        self.assertEqual(float(category3.average_grade), 100)

    def test_unweighted_incomplete_not_graded(self):
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
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 100)
        self.assertEqual(float(course.current_grade), 100)
        self.assertEqual(float(category1.average_grade), 100)

        # WHEN
        homework1.completed = True
        homework1.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 75)
        self.assertEqual(float(course.current_grade), 75)
        self.assertEqual(float(category1.average_grade), 75)

        # WHEN
        homework1.completed = False
        homework1.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 100)
        self.assertEqual(float(course.current_grade), 100)
        self.assertEqual(float(category1.average_grade), 100)

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
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 + 75 + 25 + 75 + 100) / 5
        self.assertEqual(float(course_group.overall_grade), 60)
        self.assertEqual(float(course.current_grade), 60)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='25/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='25/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 + 75 + 25 + 75 + 100 + 25 + 25) / 7
        self.assertEqual(float(course_group.overall_grade), 50)
        self.assertEqual(float(course.current_grade), 50)

        # WHEN
        homework1.current_grade = '80/100'
        homework1.save()
        homework2.current_grade = '90/100'
        homework2.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (80 + 90 + 25 + 75 + 100 + 25 + 25) / 7
        self.assertEqual(float(course_group.overall_grade), 60)
        self.assertEqual(float(course.current_grade), 60)

        # WHEN
        homework3.current_grade = '80/100'
        homework3.save()
        homework4.current_grade = '90/100'
        homework4.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (80 + 90 + 80 + 90 + 100 + 25 + 25) / 7
        self.assertEqual(float(course_group.overall_grade), 70)
        self.assertEqual(float(course.current_grade), 70)

        # WHEN
        homework3.delete()
        homework4.delete()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (80 + 90 + 100 + 25 + 25) / 5
        self.assertEqual(float(course_group.overall_grade), 64)
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
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='50/100')

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) / 90
        self.assertEqual(float(course.current_grade), 50)

        # WHEN
        homework4 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         current_grade='35/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) / 150
        self.assertEqual(float(course_group.overall_grade), 44)
        self.assertEqual(float(course.current_grade), 44)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category3, completed=True, current_grade='90/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) + (90 * 10) / 160
        self.assertEqual(float(course_group.overall_grade), 46.875)
        self.assertEqual(float(course.current_grade), 46.875)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='75/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='85/100')
        homework8 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         current_grade='45/100')

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (45 * 10) / 260
        self.assertEqual(float(course_group.overall_grade), 58.8462)
        self.assertEqual(float(course.current_grade), 58.8462)

        # WHEN
        homework4.current_grade = '80/100'
        homework4.save()
        homework8.current_grade = '80/100'
        homework8.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (80 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (80 * 10) / 260
        self.assertEqual(float(course_group.overall_grade), 70.5769)
        self.assertEqual(float(course.current_grade), 70.5769)

        # WHEN
        homework1.delete()
        homework3.delete()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        # (75 * 30) + (80 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (80 * 10) / 260
        self.assertEqual(float(course_group.overall_grade), 80.5)
        self.assertEqual(float(course.current_grade), 80.5)

    def test_weighted_course_group_grade_changes(self):
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
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         current_grade='50/100')

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) / 90
        self.assertEqual(float(course.current_grade), 50)

        # WHEN
        homework4 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         current_grade='35/100')

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) / 150
        self.assertEqual(float(course.current_grade), 44)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category3, completed=True, current_grade='90/100')

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) + (90 * 10) / 160
        self.assertEqual(float(course.current_grade), 46.875)

        # WHEN
        homeworkhelper.given_homework_exists(course, category=category1, completed=True, current_grade='75/100')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True, current_grade='85/100')
        homework8 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         current_grade='45/100')

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (35 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (45 * 10) / 260
        self.assertEqual(float(course.current_grade), 58.8462)

        # WHEN
        homework4.current_grade = '80/100'
        homework4.save()
        homework8.current_grade = '80/100'
        homework8.save()

        # THEN
        course.refresh_from_db()
        # (25 * 30) + (75 * 30) + (50 * 30) + (80 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (80 * 10) / 260
        self.assertEqual(float(course.current_grade), 70.5769)

        # WHEN
        homework1.delete()
        homework3.delete()

        # THEN
        course.refresh_from_db()
        # (75 * 30) + (80 * 60) + (90 * 10) + (75 * 30) + (85 * 60) + (80 * 10) / 260
        self.assertEqual(float(course.current_grade), 80.5)

    def test_weighted_course_group_homework_series(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        category1_1 = categoryhelper.given_category_exists(course1, weight=30)
        category1_2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        category1_3 = categoryhelper.given_category_exists(course1, title='Test Category 3', weight=20)
        category2_1 = categoryhelper.given_category_exists(course2, weight=30)
        category2_2 = categoryhelper.given_category_exists(course2, title='Test Category 2', weight=70)
        homework1_1_1 = homeworkhelper.given_homework_exists(course1, category=category1_1, completed=True,
                                                             start=datetime.datetime(2017, 4, 8, 20, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                                             current_grade='25/60')
        homework2_1_2 = homeworkhelper.given_homework_exists(course1, category=category1_2, completed=True,
                                                             start=datetime.datetime(2017, 4, 9, 20, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                                             current_grade='75/80')
        homework3_1_3 = homeworkhelper.given_homework_exists(course1, category=category1_3, completed=True,
                                                             start=datetime.datetime(2017, 4, 10, 20, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 10, 20, 30,
                                                                                   tzinfo=datetime.timezone.utc),
                                                             current_grade='50/120')
        homework4_1_1 = homeworkhelper.given_homework_exists(course1, category=category1_1, completed=True,
                                                             start=datetime.datetime(2017, 4, 11, 20, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 11, 20, 30,
                                                                                   tzinfo=datetime.timezone.utc),
                                                             current_grade='60/80')
        homework5_1_3 = homeworkhelper.given_homework_exists(course1, category=category1_3, completed=True,
                                                             start=datetime.datetime(2017, 4, 11, 20, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 11, 20, 30,
                                                                                   tzinfo=datetime.timezone.utc),
                                                             current_grade='110/130')
        homework6_2_1 = homeworkhelper.given_homework_exists(course2, category=category2_1, completed=True,
                                                             start=datetime.datetime(2017, 4, 8, 21, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 8, 21, 30, tzinfo=datetime.timezone.utc),
                                                             current_grade='25/60')
        homework7_2_2 = homeworkhelper.given_homework_exists(course2, category=category2_2, completed=True,
                                                             start=datetime.datetime(2017, 4, 9, 17, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 9, 17, 30, tzinfo=datetime.timezone.utc),
                                                             current_grade='75/80')
        homework8_2_1 = homeworkhelper.given_homework_exists(course2, category=category2_1, completed=True,
                                                             start=datetime.datetime(2017, 4, 10, 19, 0,
                                                                                     tzinfo=datetime.timezone.utc),
                                                             end=datetime.datetime(2017, 4, 10, 19, 30,
                                                                                   tzinfo=datetime.timezone.utc),
                                                             current_grade='50/120')
        course_group.refresh_from_db()

        # WHEN
        homework_series = gradingservice.get_homework_series_for_course_group(course_group.pk)
        graded = [item for item in homework_series if item['graded']]

        # THEN
        self.assertEqual(len(graded), 8)
        self.assertEqual(graded[0],
                         {'id': homework1_1_1.pk, 'title': homework1_1_1.title, 'start': homework1_1_1.start,
                          'category_id': category1_1.pk, 'course_id': course1.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 41.6667, 'cumulative_grade': 41.6667,
                          'impact_score': None})
        self.assertEqual(graded[1],
                         {'id': homework6_2_1.pk, 'title': homework6_2_1.title, 'start': homework6_2_1.start,
                          'category_id': category2_1.pk, 'course_id': course2.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 41.6667, 'cumulative_grade': 41.6667,
                          'impact_score': None})
        self.assertEqual(graded[2],
                         {'id': homework7_2_2.pk, 'title': homework7_2_2.title, 'start': homework7_2_2.start,
                          'category_id': category2_2.pk, 'course_id': course2.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 93.75, 'cumulative_grade': 59.8958,
                          'impact_score': None})
        self.assertEqual(graded[3],
                         {'id': homework2_1_2.pk, 'title': homework2_1_2.title, 'start': homework2_1_2.start,
                          'category_id': category1_2.pk, 'course_id': course1.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 93.75, 'cumulative_grade': 76.1719,
                          'impact_score': None})
        self.assertEqual(graded[4],
                         {'id': homework8_2_1.pk, 'title': homework8_2_1.title, 'start': homework8_2_1.start,
                          'category_id': category2_1.pk, 'course_id': course2.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 41.6667, 'cumulative_grade': 71.9651,
                          'impact_score': None})
        self.assertEqual(graded[5],
                         {'id': homework3_1_3.pk, 'title': homework3_1_3.title, 'start': homework3_1_3.start,
                          'category_id': category1_3.pk, 'course_id': course1.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 41.6667, 'cumulative_grade': 68.7099,
                          'impact_score': None})
        self.assertEqual(graded[6],
                         {'id': homework4_1_1.pk, 'title': homework4_1_1.title, 'start': homework4_1_1.start,
                          'category_id': category1_1.pk, 'course_id': course1.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 75, 'cumulative_grade': 69.5513,
                          'impact_score': None})
        self.assertEqual(graded[7],
                         {'id': homework5_1_3.pk, 'title': homework5_1_3.title, 'start': homework5_1_3.start,
                          'category_id': category1_3.pk, 'course_id': course1.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 84.6154, 'cumulative_grade': 70.5662,
                          'impact_score': None})

        # Final graded item should also equal the overall calculated grade
        self.assertEqual(graded[7]['cumulative_grade'], float(course_group.overall_grade))

    def test_unweighted_course_homework_series(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2')
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3')
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='25/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='50/100')
        homework4 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='60/80')
        homework5 = homeworkhelper.given_homework_exists(course, category=category3,
                                                         start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=datetime.timezone.utc),
                                                         completed=True, current_grade='4/5')
        # Incomplete homework with a real grade are excluded from both graded and ungraded series
        homeworkhelper.given_homework_exists(course, category=category1,
                                             start=datetime.datetime(2017, 4, 8, 21, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 21, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='80/100')
        course.refresh_from_db()

        # WHEN
        homework_series = gradingservice.get_homework_series_for_course(course.pk)
        graded = [item for item in homework_series if item['graded']]

        # THEN
        self.assertEqual(len(graded), 5)
        # (25) / 1
        self.assertEqual(graded[0],
                         {'id': homework1.pk, 'title': homework1.title, 'start': homework1.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 25, 'cumulative_grade': 25,
                          'impact_score': None})
        # (25 + 75) / 2
        self.assertEqual(graded[1],
                         {'id': homework2.pk, 'title': homework2.title, 'start': homework2.start,
                          'category_id': category2.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 75, 'cumulative_grade': 50,
                          'impact_score': None})
        # (25 + 75 + 50) / 3
        self.assertEqual(graded[2],
                         {'id': homework3.pk, 'title': homework3.title, 'start': homework3.start,
                          'category_id': category3.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 50, 'cumulative_grade': 50,
                          'impact_score': None})
        # (25 + 75 + 50 + (60/80)) / 4
        self.assertEqual(graded[3],
                         {'id': homework4.pk, 'title': homework4.title, 'start': homework4.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 75, 'cumulative_grade': 55.2632,
                          'impact_score': None})
        # (25 + 75 + 50 + (60/80) + (4/5)) / 5
        self.assertEqual(graded[4],
                         {'id': homework5.pk, 'title': homework5.title, 'start': homework5.start,
                          'category_id': category3.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 80, 'cumulative_grade': 55.5844,
                          'impact_score': None})

        # Final graded item should also equal the overall calculated grade
        self.assertEqual(graded[4]['cumulative_grade'], float(course.current_grade))

        # No ungraded items (the incomplete homework has current_grade != '-1/100')
        ungraded = [item for item in homework_series if not item['graded']]
        self.assertEqual(len(ungraded), 0)

    def test_weighted_course_homework_series_1(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=20)
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='80/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='90/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='72/100')
        course.refresh_from_db()

        # WHEN
        homework_series = gradingservice.get_homework_series_for_course(course.pk)
        graded = [item for item in homework_series if item['graded']]

        # THEN
        self.assertEqual(len(graded), 3)
        # (80 * 30) / 30
        self.assertEqual(graded[0],
                         {'id': homework1.pk, 'title': homework1.title, 'start': homework1.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 80, 'cumulative_grade': 80,
                          'impact_score': None})
        # ((80 * 30) + (90 * 50)) / 80
        self.assertEqual(graded[1],
                         {'id': homework2.pk, 'title': homework2.title, 'start': homework2.start,
                          'category_id': category2.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 90, 'cumulative_grade': 86.25,
                          'impact_score': None})
        # ((80 * 30) + (90 * 50) + (72 * 20)) / 100
        self.assertEqual(graded[2],
                         {'id': homework3.pk, 'title': homework3.title, 'start': homework3.start,
                          'category_id': category3.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 72, 'cumulative_grade': 83.4,
                          'impact_score': None})

        # Final graded item should also equal the overall calculated grade
        self.assertEqual(graded[2]['cumulative_grade'], float(course.current_grade))

    def test_weighted_course_homework_series_2(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=20)
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='25/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='75/100')
        homework3 = homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                                         start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='50/100')
        homework4 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='60/80')
        homework5 = homeworkhelper.given_homework_exists(course, category=category3,
                                                         start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=datetime.timezone.utc),
                                                         completed=True, current_grade='4/5')
        # Incomplete homework with a real grade are excluded from both graded and ungraded series
        homeworkhelper.given_homework_exists(course, category=category1,
                                             start=datetime.datetime(2017, 4, 8, 21, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 21, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='80/100')
        course.refresh_from_db()

        # WHEN
        homework_series = gradingservice.get_homework_series_for_course(course.pk)
        graded = [item for item in homework_series if item['graded']]

        # THEN
        self.assertEqual(len(graded), 5)
        # ((25 * 30)) / 30
        self.assertEqual(graded[0],
                         {'id': homework1.pk, 'title': homework1.title, 'start': homework1.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 25, 'cumulative_grade': 25,
                          'impact_score': None})
        # ((25 * 30) + (75 * 50)) / 80
        self.assertEqual(graded[1],
                         {'id': homework2.pk, 'title': homework2.title, 'start': homework2.start,
                          'category_id': category2.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 75, 'cumulative_grade': 56.25,
                          'impact_score': None})
        # ((25 * 30) + (75 * 50) + (50 * 20)) / 100
        self.assertEqual(graded[2],
                         {'id': homework3.pk, 'title': homework3.title, 'start': homework3.start,
                          'category_id': category3.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 50, 'cumulative_grade': 55,
                          'impact_score': None})
        # ((25 * 30) + (75 * 50) + (50 * 20) + ((60/80) * 30)) / 130
        self.assertEqual(graded[3],
                         {'id': homework4.pk, 'title': homework4.title, 'start': homework4.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 75, 'cumulative_grade': 59.6154,
                          'impact_score': None})
        # ((25 * 30) + (75 * 50) + (50 * 20) + ((60/80) * 30) + ((4/5) * 20)) / 150
        self.assertEqual(graded[4],
                         {'id': homework5.pk, 'title': homework5.title, 'start': homework5.start,
                          'category_id': category3.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 80, 'cumulative_grade': 62.3333,
                          'impact_score': None})

        # Final graded item should also equal the overall calculated grade
        self.assertEqual(graded[4]['cumulative_grade'], float(course.current_grade))

        # No ungraded items (the incomplete homework has current_grade != '-1/100')
        ungraded = [item for item in homework_series if not item['graded']]
        self.assertEqual(len(ungraded), 0)

    def test_weighted_course_homework_series_total_not_100(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        homework1 = homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                                         start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='80/100')
        homework2 = homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                                         start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                                         current_grade='90/100')
        course.refresh_from_db()

        # WHEN
        homework_series = gradingservice.get_homework_series_for_course(course.pk)
        graded = [item for item in homework_series if item['graded']]

        # THEN
        self.assertEqual(len(graded), 2)
        # ((80 * 30)) / 30
        self.assertEqual(graded[0],
                         {'id': homework1.pk, 'title': homework1.title, 'start': homework1.start,
                          'category_id': category1.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 80, 'cumulative_grade': 80,
                          'impact_score': None})
        # ((80 * 30) + (90 * 50)) / 80
        self.assertEqual(graded[1],
                         {'id': homework2.pk, 'title': homework2.title, 'start': homework2.start,
                          'category_id': category2.pk, 'course_id': course.pk, 'points_possible': None,
                          'graded': True, 'homework_grade': 90, 'cumulative_grade': 86.25,
                          'impact_score': None})

        # Final graded item should also equal the overall calculated grade
        self.assertEqual(graded[1]['cumulative_grade'], float(course.current_grade))

    def test_category_changed_deleted_weighted_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course, weight=30)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course, title='Test Category 3', weight=20)
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='25/60')
        homeworkhelper.given_homework_exists(course, category=category2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='75/80')
        homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='50/120')
        homeworkhelper.given_homework_exists(course, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='60/80')
        homeworkhelper.given_homework_exists(course, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='110/130')
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        # ((25/60) * 30) + ((75/80) * 50) + ((50/120) * 20) + ((60/80) * 30) + ((110/130) * 20) / 150
        self.assertEqual(float(course_group.overall_grade), 71.4209)
        self.assertEqual(float(course.current_grade), 71.4209)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 18.2143)

        # WHEN
        category2.weight = 30
        category2.save()
        category1.weight = 50
        category1.save()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        # ((25/60) * 50) + ((75/80) * 30) + ((50/120) * 20) + ((60/80) * 50) + ((110/130) * 20) / 150
        self.assertEqual(float(course_group.overall_grade), 65.7146)
        self.assertEqual(float(course.current_grade), 65.7146)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 30.3571)
        self.assertEqual(float(category2.average_grade), 93.75)
        self.assertEqual(float(category2.grade_by_weight), 28.125)

        # WHEN
        category2.delete()

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category1.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 59.707)
        self.assertEqual(float(course.current_grade), 59.707)
        self.assertEqual(float(category1.average_grade), 60.7143)
        self.assertEqual(float(category1.grade_by_weight), 30.3571)

    def test_category_changed_deleted_weighted_grade_changes_multiple_courses(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        category1_1 = categoryhelper.given_category_exists(course1, weight=30)
        category1_2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        category1_3 = categoryhelper.given_category_exists(course1, title='Test Category 3', weight=20)
        category2_1 = categoryhelper.given_category_exists(course2, weight=30)
        category2_2 = categoryhelper.given_category_exists(course2, title='Test Category 2', weight=70)
        homeworkhelper.given_homework_exists(course1, category=category1_1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='25/60')
        homeworkhelper.given_homework_exists(course1, category=category1_2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='75/80')
        homeworkhelper.given_homework_exists(course1, category=category1_3, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='50/120')
        homeworkhelper.given_homework_exists(course1, category=category1_1, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='60/80')
        homeworkhelper.given_homework_exists(course1, category=category1_3, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='110/130')
        homeworkhelper.given_homework_exists(course2, category=category2_1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='25/60')
        homeworkhelper.given_homework_exists(course2, category=category2_2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='75/80')
        homeworkhelper.given_homework_exists(course2, category=category2_1, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='50/120')
        course_group.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 70.5662)
        self.assertEqual(float(course1.current_grade), 71.4209)
        self.assertEqual(float(course2.current_grade), 69.7115)

        # WHEN
        category1_2.weight = 30
        category1_2.save()
        category1_1.weight = 50
        category1_1.save()

        # THEN
        course_group.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 67.7131)
        self.assertEqual(float(course1.current_grade), 65.7146)
        self.assertEqual(float(course2.current_grade), 69.7115)

        # WHEN
        category1_2.delete()

        # THEN
        course_group.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 64.7092)
        self.assertEqual(float(course1.current_grade), 59.707)
        self.assertEqual(float(course2.current_grade), 69.7115)

    def test_course_deleted_weighted_grade_changes(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course1, weight=30)
        category2 = categoryhelper.given_category_exists(course1, title='Test Category 2', weight=50)
        category3 = categoryhelper.given_category_exists(course2, title='Test Category 3', weight=20)
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 8, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 8, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='25/100')
        homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                             start=datetime.datetime(2017, 4, 9, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 9, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='75/100')
        homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                             start=datetime.datetime(2017, 4, 10, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 10, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='50/100')
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                             start=datetime.datetime(2017, 4, 11, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 11, 20, 30, tzinfo=datetime.timezone.utc),
                                             current_grade='60/80')
        homeworkhelper.given_homework_exists(course2, category=category3,
                                             start=datetime.datetime(2017, 4, 12, 20, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 4, 12, 20, 30, tzinfo=datetime.timezone.utc),
                                             completed=True, current_grade='4/5')
        course_group.refresh_from_db()
        # Course 1: ((25 * 30) + (75 * 50) + ((60/80) * 30)) / 110 = 61.36
        # Course 2: ((50 * 20) + ((4/5) * 20)) / 40 = 61.36 = 65.00
        self.assertEqual(float(course_group.overall_grade), 63.1818)

        # WHEN
        course2.delete()

        # THEN
        course_group.refresh_from_db()
        self.assertEqual(float(course_group.overall_grade), 61.3636)

    def test_poisoned_zero_denominator_skipped(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        homeworkhelper.given_homework_exists(course, category=category, completed=True, current_grade='80/100')
        poisoned = homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                                       current_grade='50/100')
        # Bypass validators to simulate legacy poisoned data
        Homework.objects.filter(pk=poisoned.pk).update(current_grade='5/0')

        # WHEN
        gradingservice.recalculate_category_grade(category.pk)
        gradingservice.recalculate_course_grade(course.pk)
        gradingservice.recalculate_course_group_grade(course_group.pk)

        # THEN
        course_group.refresh_from_db()
        course.refresh_from_db()
        category.refresh_from_db()
        self.assertEqual(float(category.average_grade), 80)
        self.assertEqual(float(course.current_grade), 80)
        self.assertEqual(float(course_group.overall_grade), 80)

    def test_build_ungraded_series_items_empty(self):
        # GIVEN / WHEN
        result = gradingservice._build_ungraded_series_items(
            has_weighted_grading=True,
            categories=[],
            raw_ungraded=[]
        )

        # THEN
        self.assertEqual(result, [])

    def test_build_ungraded_series_items_nonweighted_fields_and_order(self):
        # GIVEN
        start_a = datetime.datetime(2026, 5, 10, tzinfo=datetime.timezone.utc)
        start_b = datetime.datetime(2026, 5, 20, tzinfo=datetime.timezone.utc)
        raw_ungraded = [
            {'id': 1, 'title': 'Assignment A', 'start': start_a, 'course_id': 1, 'category_id': 10, 'current_grade': '-1/100'},
            {'id': 2, 'title': 'Assignment B', 'start': start_b, 'course_id': 1, 'category_id': 10, 'current_grade': '-1/100'},
        ]

        # WHEN
        result = gradingservice._build_ungraded_series_items(
            has_weighted_grading=False,
            categories=[],
            raw_ungraded=raw_ungraded
        )

        # THEN — correct shape, start order preserved, no impact_score for non-weighted
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 1)
        self.assertEqual(result[1]['id'], 2)
        self.assertEqual(result[0]['points_possible'], 100.0)
        self.assertFalse(result[0]['graded'])
        self.assertIsNone(result[0]['homework_grade'])
        self.assertIsNone(result[0]['cumulative_grade'])
        self.assertIsNone(result[0]['impact_score'])

    def test_build_ungraded_series_items_weighted_impact_score_set(self):
        # GIVEN — two categories with different weights; verify impact_score is attached
        start_early = datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc)
        start_late = datetime.datetime(2026, 5, 30, tzinfo=datetime.timezone.utc)
        categories = [
            {'id': 10, 'weight': 30, 'num_homework': 2, 'num_homework_graded': 1, 'overall_grade': 80.0},
            {'id': 20, 'weight': 60, 'num_homework': 2, 'num_homework_graded': 1, 'overall_grade': 70.0},
        ]
        raw_ungraded = [
            {'id': 1, 'title': 'Low Impact', 'start': start_early, 'course_id': 1, 'category_id': 10, 'current_grade': '-1/100'},
            {'id': 2, 'title': 'High Impact', 'start': start_late, 'course_id': 1, 'category_id': 20, 'current_grade': '-1/100'},
        ]

        # WHEN
        result = gradingservice._build_ungraded_series_items(
            has_weighted_grading=True,
            categories=categories,
            raw_ungraded=raw_ungraded
        )

        # THEN — impact_score set per category; cat 20 has higher score than cat 10
        item_cat10 = next(r for r in result if r['category_id'] == 10)
        item_cat20 = next(r for r in result if r['category_id'] == 20)
        self.assertIsNotNone(item_cat10['impact_score'])
        self.assertIsNotNone(item_cat20['impact_score'])
        self.assertGreater(item_cat20['impact_score'], item_cat10['impact_score'])

    def test_build_ungraded_series_items_skips_zero_denominator(self):
        # GIVEN
        raw_ungraded = [
            {'id': 1, 'title': 'Poisoned', 'start': datetime.datetime(2026, 5, 1, tzinfo=datetime.timezone.utc),
             'course_id': 1, 'category_id': 10, 'current_grade': '-1/0'},
            {'id': 2, 'title': 'Valid', 'start': datetime.datetime(2026, 5, 2, tzinfo=datetime.timezone.utc),
             'course_id': 1, 'category_id': 10, 'current_grade': '-1/100'},
        ]

        # WHEN
        result = gradingservice._build_ungraded_series_items(
            has_weighted_grading=False,
            categories=[],
            raw_ungraded=raw_ungraded
        )

        # THEN — poisoned entry silently skipped
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 2)

    def test_build_homework_series_combines_graded_and_ungraded_sorted_by_start(self):
        # GIVEN — one graded tuple and one ungraded raw item
        graded_start = datetime.datetime(2026, 4, 1, tzinfo=datetime.timezone.utc)
        ungraded_start = datetime.datetime(2026, 5, 15, tzinfo=datetime.timezone.utc)
        grade_points = [
            [graded_start, 85.0, 10, 'Quiz 1', 85.0, 5, 1],
        ]
        raw_ungraded = [
            {'id': 20, 'title': 'Final Exam', 'start': ungraded_start,
             'course_id': 1, 'category_id': 5, 'current_grade': '-1/100'},
        ]

        # WHEN
        result = gradingservice._build_homework_series(
            grade_points=grade_points,
            has_weighted_grading=False,
            categories=[],
            raw_ungraded=raw_ungraded
        )

        # THEN — graded item first, ungraded second; correct shapes
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0]['graded'])
        self.assertEqual(result[0]['id'], 10)
        self.assertEqual(result[0]['cumulative_grade'], 85.0)
        self.assertIsNone(result[0]['impact_score'])
        self.assertFalse(result[1]['graded'])
        self.assertEqual(result[1]['id'], 20)
        self.assertIsNone(result[1]['cumulative_grade'])
