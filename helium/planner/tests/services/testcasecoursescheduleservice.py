import datetime
from unittest import mock

from django.db import IntegrityError, transaction
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
                         [datetime.datetime(2026, 4, 1, 9, 0, 0, tzinfo=datetime.timezone.utc)])

    def test_resolve_cycle_index_counts_school_days_and_shifts_across_the_weekend(self):
        # GIVEN
        schedule = CourseSchedule(cycle_length=2, anchor_date=datetime.date(2026, 3, 2))

        # WHEN/THEN
        self.assertEqual(schedule.anchor_date.weekday(), 0)
        self.assertEqual(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 2), set()), 1)
        self.assertEqual(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 3), set()), 2)
        self.assertEqual(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 6), set()), 1)
        # 5 school days Mon-Fri is odd relative to a 2-day cycle, so the next Monday is Day 2, not Day 1
        self.assertEqual(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 9), set()), 2)
        # weekend and pre-anchor dates have no cycle index
        self.assertIsNone(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 7), set()))
        self.assertIsNone(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 1), set()))

    def test_resolve_cycle_index_holiday_shifts_the_count(self):
        # GIVEN
        schedule = CourseSchedule(cycle_length=2, anchor_date=datetime.date(2026, 3, 2))
        exceptions = {datetime.date(2026, 3, 3)}

        # WHEN/THEN
        # Without the holiday Wed is Day 1; with Tuesday skipped, Wed becomes the 2nd school day → Day 2
        self.assertEqual(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 4), exceptions), 2)
        self.assertIsNone(coursescheduleservice.resolve_cycle_index(schedule, datetime.date(2026, 3, 3), exceptions))

    def test_resolve_week_index_counts_calendar_weeks(self):
        # GIVEN
        schedule = CourseSchedule(is_week_based=True, week_offset=0, anchor_date=datetime.date(2026, 3, 2))

        # WHEN/THEN
        # shift it, unlike a day cycle.
        self.assertEqual(schedule.anchor_date.weekday(), 0)
        self.assertEqual(coursescheduleservice.resolve_week_index(schedule, datetime.date(2026, 3, 2)), 0)
        self.assertEqual(coursescheduleservice.resolve_week_index(schedule, datetime.date(2026, 3, 6)), 0)
        self.assertEqual(coursescheduleservice.resolve_week_index(schedule, datetime.date(2026, 3, 9)), 1)
        # A full rotation later returns to the anchor week (mod 2).
        self.assertEqual(coursescheduleservice.resolve_week_index(schedule, datetime.date(2026, 3, 16)), 0)

    def test_course_schedule_to_recurrence_groups_cycle(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 13))
        course_schedule = courseschedulehelper.given_cycle_schedule_exists(
            course, cycle_length=2, anchor_date=datetime.date(2026, 3, 2),
            cycle_slots=[
                {'indices': [1], 'start_time': '09:00:00', 'end_time': '09:50:00'},
                {'indices': [2], 'start_time': '14:00:00', 'end_time': '14:50:00'},
            ])

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 2)
        day_1_group = next(g for g in groups if g.start.hour == 9)
        day_2_group = next(g for g in groups if g.start.hour == 14)

        # Both are the same all-school-weekday superset RRULE; the cycle lives entirely in the exclusions.
        for group in groups:
            self.assertEqual(group.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;UNTIL=20260313T235959Z')

        # Day 1 meets at 9am on the odd school days; the even (Day 2) school days are excluded.
        self.assertEqual(day_1_group.start.date(), datetime.date(2026, 3, 2))
        self.assertEqual({e.date() for e in day_1_group.exception_dates},
                         {datetime.date(2026, 3, 3), datetime.date(2026, 3, 5), datetime.date(2026, 3, 9),
                          datetime.date(2026, 3, 11), datetime.date(2026, 3, 13)})

        # Day 2 meets at 2pm on the even school days; the odd (Day 1) school days are excluded — but
        # only those on/after this group's first occurrence (its RRULE anchor), so 03-02 isn't listed.
        self.assertEqual(day_2_group.start.date(), datetime.date(2026, 3, 3))
        self.assertEqual({e.date() for e in day_2_group.exception_dates},
                         {datetime.date(2026, 3, 4), datetime.date(2026, 3, 6),
                          datetime.date(2026, 3, 10), datetime.date(2026, 3, 12)})

    def test_course_schedule_to_recurrence_groups_week_based(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 27))
        course_schedule = courseschedulehelper.given_week_based_schedule_exists(
            course, days_of_week='0100000', week_offset=0, anchor_date=datetime.date(2026, 3, 2))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group.recurrence_rule, 'FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;UNTIL=20260327T235959Z')
        self.assertEqual(group.start.date(), datetime.date(2026, 3, 2))
        self.assertEqual(group.start.hour, 9)
        self.assertEqual(group.exception_dates, [])

    def test_single_rotation_type_constraint_rejects_both_rotation_types(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN/THEN
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CourseSchedule.objects.create(course=course, cycle_length=2, is_week_based=True)

    def test_course_schedule_to_recurrence_groups_week_based_excludes_exception_date(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 27))
        course.exceptions = '20260316'
        course.save()
        course_schedule = courseschedulehelper.given_week_based_schedule_exists(
            course, days_of_week='0100000', week_offset=0, anchor_date=datetime.date(2026, 3, 2))

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, course_schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        self.assertIn(datetime.datetime(2026, 3, 16, 9, 0, 0, tzinfo=datetime.timezone.utc),
                      groups[0].exception_dates)

    def test_schedule_window_falls_back_to_course_and_clamps(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 1, 5), end_date=datetime.date(2026, 5, 1))
        schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN / THEN
        # No overrides → the course's own dates.
        self.assertEqual(coursescheduleservice.schedule_window(course, schedule),
                         (datetime.date(2026, 1, 5), datetime.date(2026, 5, 1)))
        # A narrower override → used as-is.
        schedule.start_date = datetime.date(2026, 1, 12)
        schedule.end_date = datetime.date(2026, 4, 24)
        self.assertEqual(coursescheduleservice.schedule_window(course, schedule),
                         (datetime.date(2026, 1, 12), datetime.date(2026, 4, 24)))
        # A window wider than the course → clamped to the course window.
        schedule.start_date = datetime.date(2025, 12, 1)
        schedule.end_date = datetime.date(2026, 6, 1)
        self.assertEqual(coursescheduleservice.schedule_window(course, schedule),
                         (datetime.date(2026, 1, 5), datetime.date(2026, 5, 1)))

    def test_course_schedule_to_recurrence_groups_respects_schedule_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 27))
        schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0100000',
            mon_start_time=datetime.time(9, 0, 0), mon_end_time=datetime.time(9, 50, 0))
        schedule.start_date = datetime.date(2026, 3, 9)
        schedule.end_date = datetime.date(2026, 3, 20)
        schedule.save()

        # WHEN
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(course, schedule)

        # THEN
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].start.date(), datetime.date(2026, 3, 9))
        self.assertIn('UNTIL=20260320T235959Z', groups[0].recurrence_rule)

    def test_course_schedules_to_events_cycle_emits_matching_cycle_days(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 6))
        courseschedulehelper.given_cycle_schedule_exists(
            course, cycle_length=2, anchor_date=datetime.date(2026, 3, 2),
            cycle_slots=[{'indices': [1], 'start_time': '09:00:00', 'end_time': '09:50:00'}])

        # WHEN
        events = coursescheduleservice.course_schedules_to_events(course, course.schedules)

        # THEN
        self.assertEqual({event.start.date() for event in events},
                         {datetime.date(2026, 3, 2), datetime.date(2026, 3, 4), datetime.date(2026, 3, 6)})
        self.assertTrue(all(event.start.time() == datetime.time(9, 0, 0) for event in events))

    def test_course_schedule_to_recurrence_groups_exception_shares_utc_date_with_occurrence_in_positive_offset_tz(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'Asia/Kolkata'
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
        # 09:00 IST (UTC+5:30) is 03:30Z on the same calendar day; anchoring the exception at the
        # slot start (not midnight, which would land on 2026-03-31 in UTC) keeps its UTC date aligned
        # with the occurrence it must cancel.
        self.assertEqual(groups[0].exception_dates,
                         [datetime.datetime(2026, 4, 1, 3, 30, 0, tzinfo=datetime.timezone.utc)])
        # Occurrences all share the slot's UTC time-of-day, so an exception at that same time-of-day
        # lands on the same UTC date as the occurrence it cancels.
        self.assertEqual(groups[0].exception_dates[0].timetz(), groups[0].start.timetz())
