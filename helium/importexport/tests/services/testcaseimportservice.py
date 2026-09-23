import datetime
import json
import os
from unittest.mock import PropertyMock, patch

from django.db import connection
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.importexport.services import importservice
from helium.importexport.services.importservice import import_example_schedule
from helium.planner.models import CourseGroup, CourseSchedule, Homework
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, reminderhelper


class TestCaseImportService(TestCase):
    def _create_user_with_timezone(self, tz_name):
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = tz_name
        user.settings.save()
        return user

    def test_example_schedule_remaps_categories_when_bulk_insert_returns_no_pks(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        with open(os.path.join(os.path.dirname(importservice.__file__), '..', 'resources',
                               'example_schedule.json'), 'rb') as f:
            data = json.loads(f.read().decode('utf-8'))
        course_titles = {c['id']: c['title'] for c in data['courses']}
        category_titles = {c['id']: c['title'] for c in data['categories']}
        expected = sorted(
            (h['title'], course_titles[h['course']], category_titles[h['category']])
            for h in data['homework'] if h.get('category'))

        # WHEN
        with patch.object(type(connection.features), 'can_return_rows_from_bulk_insert', new_callable=PropertyMock,
                          return_value=False):
            import_example_schedule(user)

        # THEN
        actual = sorted(Homework.objects.for_user(user.pk).filter(category__title__in=set(category_titles.values()))
                        .exclude(category__title='Uncategorized')
                        .values_list('title', 'course__title', 'category__title'))
        self.assertEqual([e for e in expected if e[2] != 'Uncategorized'], actual)
        self.assertTrue(all(h.category.course_id == h.course_id
                            for h in Homework.objects.for_user(user.pk).select_related('category')))

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_uses_user_timezone_when_behind_utc_at_month_boundary(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 4, 1, 0, 30, 0, tzinfo=datetime.timezone.utc)
        user = self._create_user_with_timezone('America/New_York')

        # WHEN
        import_example_schedule(user)

        # THEN
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 2, 2),
        )

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_uses_utc_month_when_user_timezone_is_utc(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 4, 1, 0, 30, 0, tzinfo=datetime.timezone.utc)
        user = self._create_user_with_timezone('UTC')

        # WHEN
        import_example_schedule(user)

        # THEN
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 3, 2),
        )

    @patch('django.utils.timezone.now')
    def test_adjust_schedule_day_before_utc_month_boundary(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 31, 23, 30, 0, tzinfo=datetime.timezone.utc)
        user = self._create_user_with_timezone('America/New_York')

        # WHEN
        import_example_schedule(user)

        # THEN
        self.assertEqual(
            CourseGroup.objects.filter(user=user).first().start_date,
            datetime.date(2026, 2, 2),
        )

    def test_get_most_recent_course_occurrence_start_uses_latest_of_multiple_schedules_same_day(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()

        day_names = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
        target_day = datetime.date.today() - datetime.timedelta(days=1)
        weekday = enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[target_day.weekday()]
        days_of_week = ['0'] * 7
        days_of_week[weekday] = '1'
        days_of_week = ''.join(days_of_week)

        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=target_day - datetime.timedelta(days=30),
            end_date=target_day
        )
        # `CourseSchedule.course` enforces unique=True, so a second schedule can't be persisted
        # for the same course — build it in memory and patch the queryset to simulate it.
        earlier_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week=days_of_week,
            **{f'{day_names[weekday]}_start_time': datetime.time(9, 0, 0)})
        later_schedule = CourseSchedule(course=course, days_of_week=days_of_week,
                                        **{f'{day_names[weekday]}_start_time': datetime.time(14, 0, 0)})
        reminder = reminderhelper.given_reminder_exists(user, course=course, type=enums.PUSH, sent=True)

        # WHEN
        with patch.object(type(course.schedules), 'all', return_value=[earlier_schedule, later_schedule]):
            result = importservice._get_most_recent_course_occurrence_start(reminder)

        # THEN
        expected = datetime.datetime.combine(target_day, datetime.time(14, 0, 0), tzinfo=datetime.timezone.utc)
        self.assertEqual(result, expected)
