__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest import mock

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseSchedule
from helium.planner.services import coursescheduleservice
from helium.planner.services.coursescheduleservice import HeliumCourseScheduleError
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper


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

    def test_course_schedules_to_events_includes_every_schedule_active_same_day(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 3, 25),
            end_date=datetime.date(2026, 3, 25)
        )
        # `CourseSchedule.course` enforces unique=True, so a second schedule can't be persisted
        # for the same course — build it in memory and pass both via a stub queryset.
        schedule_a = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0001000',
            wed_start_time=datetime.time(9, 0, 0), wed_end_time=datetime.time(9, 50, 0))
        schedule_b = CourseSchedule(course=course, days_of_week='0001000',
                                    wed_start_time=datetime.time(14, 0, 0), wed_end_time=datetime.time(14, 50, 0))
        course_schedules = mock.MagicMock()
        course_schedules.all.return_value = [schedule_a, schedule_b]

        # WHEN
        events = coursescheduleservice.course_schedules_to_events(course, course_schedules)

        # THEN
        self.assertEqual(len(events), 2)
        self.assertEqual({event.start.time() for event in events},
                         {datetime.time(9, 0, 0), datetime.time(14, 0, 0)})

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
        self.assertEqual(comments1, '<a href="http://mycourse.com">🧪 Test Course</a> in DNC 201')
        self.assertEqual(comments2, '<a href="http://mycourse.com">🧪 Test Course</a>')
        self.assertEqual(comments3, '')

    def test_course_schedule_to_recurrence_groups_single_day(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 23), end_date=datetime.date(2026, 4, 30))
        course_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0001000',
            wed_start_time=datetime.time(9, 0, 0), wed_end_time=datetime.time(9, 50, 0))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].start, datetime.datetime(2026, 3, 25, 9, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(groups[0].end, datetime.datetime(2026, 3, 25, 9, 50, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(groups[0].recurrence_rule, 'FREQ=WEEKLY;BYDAY=WE;UNTIL=20260430T235959Z')
        self.assertEqual(groups[0].exception_dates, [])

    def test_course_schedule_to_recurrence_groups_multiple_days_same_time(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 23), end_date=datetime.date(2026, 4, 30))
        course_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0101010',
            mon_start_time=datetime.time(10, 0, 0), mon_end_time=datetime.time(10, 50, 0),
            wed_start_time=datetime.time(10, 0, 0), wed_end_time=datetime.time(10, 50, 0),
            fri_start_time=datetime.time(10, 0, 0), fri_end_time=datetime.time(10, 50, 0))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].start, datetime.datetime(2026, 3, 23, 10, 0, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(groups[0].recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20260430T235959Z')

    def test_course_schedule_to_recurrence_groups_multiple_days_different_times(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 23), end_date=datetime.date(2026, 4, 30))
        course_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0101010',
            mon_start_time=datetime.time(9, 0, 0), mon_end_time=datetime.time(9, 50, 0),
            wed_start_time=datetime.time(9, 0, 0), wed_end_time=datetime.time(9, 50, 0),
            fri_start_time=datetime.time(14, 0, 0), fri_end_time=datetime.time(14, 50, 0))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 2)
        self.assertEqual({group.recurrence_rule for group in groups}, {
            'FREQ=WEEKLY;BYDAY=MO,WE;UNTIL=20260430T235959Z',
            'FREQ=WEEKLY;BYDAY=FR;UNTIL=20260430T235959Z',
        })

    def test_course_schedule_to_recurrence_groups_excludes_course_exception_date(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 23), end_date=datetime.date(2026, 4, 30))
        course.exceptions = '20260401'
        course.save()
        course_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0001000',
            wed_start_time=datetime.time(9, 0, 0), wed_end_time=datetime.time(9, 50, 0))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].exception_dates,
                         [datetime.datetime(2026, 4, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)])
