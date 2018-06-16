import datetime

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.services import coursescheduleservice
from helium.planner.services.coursescheduleservice import HeliumCourseScheduleError
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.21'


class TestCaseCourseScheduleService(TestCase):
    def test_get_start_time_for_weekday(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                                            sun_start_time=datetime.time(12, 0, 0),
                                                                            mon_start_time=datetime.time(12, 0, 1),
                                                                            tue_start_time=datetime.time(12, 0, 2),
                                                                            wed_start_time=datetime.time(12, 0, 3),
                                                                            thu_start_time=datetime.time(12, 0, 4),
                                                                            fri_start_time=datetime.time(12, 0, 5),
                                                                            sat_start_time=datetime.time(12, 0, 6))

        # WHEN
        day_0 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 0)
        day_1 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 1)
        day_2 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 2)
        day_3 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 3)
        day_4 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 4)
        day_5 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 5)
        day_6 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 6)

        # THEN
        self.assertEqual(day_0, datetime.time(12, 0, 0))
        self.assertEqual(day_1, datetime.time(12, 0, 1))
        self.assertEqual(day_2, datetime.time(12, 0, 2))
        self.assertEqual(day_3, datetime.time(12, 0, 3))
        self.assertEqual(day_4, datetime.time(12, 0, 4))
        self.assertEqual(day_5, datetime.time(12, 0, 5))
        self.assertEqual(day_6, datetime.time(12, 0, 6))
        self.assertRaises(HeliumCourseScheduleError,
                          coursescheduleservice._get_start_time_for_weekday, course_schedule, 7)

        # WHEN
        course_schedule.days_of_week = '1011111'
        course_schedule.save()
        day_0 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 0)
        day_1 = coursescheduleservice._get_start_time_for_weekday(course_schedule, 1)

        # THEN
        self.assertIsNotNone(day_0)
        self.assertIsNone(day_1)

    def test_get_end_time_for_weekday(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                                            sun_end_time=datetime.time(3, 0, 0),
                                                                            mon_end_time=datetime.time(3, 0, 1),
                                                                            tue_end_time=datetime.time(3, 0, 2),
                                                                            wed_end_time=datetime.time(3, 0, 3),
                                                                            thu_end_time=datetime.time(3, 0, 4),
                                                                            fri_end_time=datetime.time(3, 0, 5),
                                                                            sat_end_time=datetime.time(3, 0, 6))

        # WHEN
        day_0 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 0)
        day_1 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 1)
        day_2 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 2)
        day_3 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 3)
        day_4 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 4)
        day_5 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 5)
        day_6 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 6)

        # THEN
        self.assertEqual(day_0, datetime.time(3, 0, 0))
        self.assertEqual(day_1, datetime.time(3, 0, 1))
        self.assertEqual(day_2, datetime.time(3, 0, 2))
        self.assertEqual(day_3, datetime.time(3, 0, 3))
        self.assertEqual(day_4, datetime.time(3, 0, 4))
        self.assertEqual(day_5, datetime.time(3, 0, 5))
        self.assertEqual(day_6, datetime.time(3, 0, 6))
        self.assertRaises(HeliumCourseScheduleError,
                          coursescheduleservice._get_end_time_for_weekday, course_schedule, 7)

        # WHEN
        course_schedule.days_of_week = '1011111'
        course_schedule.save()
        day_0 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 0)
        day_1 = coursescheduleservice._get_end_time_for_weekday(course_schedule, 1)

        # THEN
        self.assertIsNotNone(day_0)
        self.assertIsNone(day_1)

    def test_get_comments(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        comments1 = coursescheduleservice._get_comments(course)
        course.is_online = True
        course.save()
        comments2 = coursescheduleservice._get_comments(course)
        course.website = None
        course.save()
        comments3 = coursescheduleservice._get_comments(course)

        # THEN
        self.assertEqual(comments1, '<a href="http://mycourse.com">Test Course</a> in DNC 201')
        self.assertEqual(comments2, '<a href="http://mycourse.com">Test Course</a>')
        self.assertEqual(comments3, '')
