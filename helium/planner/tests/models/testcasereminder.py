__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, eventhelper, reminderhelper


class TestCaseReminder(TestCase):
    def test_parent_change_triggers_reminder_update(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder1 = reminderhelper.given_reminder_exists(user, event=event)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework)

        # WHEN
        event.start = datetime.datetime(2019, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        event.save()
        homework.start = datetime.datetime(2019, 1, 8, 10, 0, 0, tzinfo=timezone.utc)
        homework.save()

        # THEN
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        self.assertEqual(reminder1.start_of_range, datetime.datetime(2019, 5, 8, 11, 45, 0, tzinfo=timezone.utc))
        self.assertEqual(reminder2.start_of_range, datetime.datetime(2019, 1, 8, 9, 45, 0, tzinfo=timezone.utc))

    def test_send_window_excludes_stale_reminders(self):
        # GIVEN a reminder whose start_of_range is just outside the send window
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        beyond_window = timezone.now() - datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES + 1)
        Reminder.objects.filter(pk=reminder.pk).update(start_of_range=beyond_window)

        # THEN it is not queued for sending
        self.assertNotIn(reminder, Reminder.objects.for_today())

        # WHEN its start_of_range is moved back inside the window
        within_window = timezone.now() - datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES - 1)
        Reminder.objects.filter(pk=reminder.pk).update(start_of_range=within_window)

        # THEN it is queued for sending
        self.assertIn(reminder, Reminder.objects.for_today())
