import os
from unittest import mock
from zoneinfo import ZoneInfo

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup


class TestCaseImportScheduleCommand(TestCase):
    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_import_rebases_imported_course_groups_to_the_previous_month(self, mock_validate_url):
        # GIVEN
        user = userhelper.given_a_user_exists()
        path = os.path.join(os.path.dirname(__file__), 'resources', 'sample.json')

        # WHEN
        call_command('importschedule', user.pk, path)

        # THEN
        now = timezone.now().astimezone(ZoneInfo(user.settings.time_zone))
        years_back, month_index = divmod(now.month - 2, 12)
        course_groups = CourseGroup.objects.for_user(user.pk)
        self.assertTrue(course_groups.exists())
        for course_group in course_groups:
            self.assertEqual((now.year + years_back, month_index + 1),
                             (course_group.start_date.year, course_group.start_date.month))
            self.assertEqual(0, course_group.start_date.weekday())
