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

    def test_event_date_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN a sent reminder on a past event
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)  # default start=2017-05-08 12:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN only the date portion of event.start is moved to a future date (keeping same time)
        new_start = datetime.datetime(2030, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=1)
        event.save()

        # THEN start_of_range is recalculated to the exact expected value, and sent is reset
        # because the new start_of_range is in the future (reminder will re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 11, 45, 0, tzinfo=timezone.utc))
        self.assertFalse(reminder.sent)

    def test_event_date_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN a sent reminder on the default 2017 event
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)  # default start=2017-05-08 12:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN only the date is moved further into the past
        new_start = datetime.datetime(2016, 5, 8, 12, 0, 0, tzinfo=timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN start_of_range reflects the new date exactly; sent remains True because
        # the new start_of_range is well outside the send window (reminder will not re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2016, 5, 8, 11, 45, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)

    def test_event_time_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN a sent reminder on a future event
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user,
                                               start=datetime.datetime(2030, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
                                               end=datetime.datetime(2030, 5, 8, 14, 0, 0, tzinfo=timezone.utc))
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN only the time portion changes (same date 2030-05-08, moved from 12:00 to 14:00)
        new_start = datetime.datetime(2030, 5, 8, 14, 0, 0, tzinfo=timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN start_of_range is recalculated exactly and sent is reset because the new
        # start_of_range is in the future (reminder will re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 13, 45, 0, tzinfo=timezone.utc))
        self.assertFalse(reminder.sent)

    def test_event_time_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN a sent reminder on the default 2017 event
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)  # default start=2017-05-08 12:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN only the time portion changes (same date, earlier time)
        new_start = datetime.datetime(2017, 5, 8, 10, 0, 0, tzinfo=timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN start_of_range reflects the new time exactly; sent remains True because
        # the new start_of_range is well outside the send window (reminder will not re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2017, 5, 8, 9, 45, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)

    def test_homework_date_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN a sent reminder on a past homework assignment
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)  # default start=2017-05-08 16:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN only the date portion of homework.start is moved to a future date (keeping same time)
        new_start = datetime.datetime(2030, 5, 8, 16, 0, 0, tzinfo=timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN start_of_range is recalculated to the exact expected value, and sent is reset
        # because the new start_of_range is in the future (reminder will re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 15, 45, 0, tzinfo=timezone.utc))
        self.assertFalse(reminder.sent)

    def test_homework_date_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN a sent reminder on the default 2017 homework
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)  # default start=2017-05-08 16:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN only the date is moved further into the past
        new_start = datetime.datetime(2016, 5, 8, 16, 0, 0, tzinfo=timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN start_of_range reflects the new date exactly; sent remains True because
        # the new start_of_range is well outside the send window (reminder will not re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2016, 5, 8, 15, 45, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)

    def test_homework_time_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN a sent reminder on a future homework assignment
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=datetime.datetime(2030, 5, 8, 16, 0, 0, tzinfo=timezone.utc),
                                                        end=datetime.datetime(2030, 5, 8, 18, 0, 0, tzinfo=timezone.utc))
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN only the time portion changes (same date 2030-05-08, moved from 16:00 to 18:00)
        new_start = datetime.datetime(2030, 5, 8, 18, 0, 0, tzinfo=timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN start_of_range is recalculated exactly and sent is reset because the new
        # start_of_range is in the future (reminder will re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 17, 45, 0, tzinfo=timezone.utc))
        self.assertFalse(reminder.sent)

    def test_homework_time_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN a sent reminder on the default 2017 homework
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)  # default start=2017-05-08 16:00 UTC
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN only the time portion changes to an earlier time on the same date
        new_start = datetime.datetime(2017, 5, 8, 14, 0, 0, tzinfo=timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN start_of_range reflects the new time exactly; sent remains True because
        # the new start_of_range is well outside the send window (reminder will not re-fire)
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2017, 5, 8, 13, 45, 0, tzinfo=timezone.utc))
        self.assertTrue(reminder.sent)
