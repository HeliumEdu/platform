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
        event.start = datetime.datetime(2019, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.save()
        homework.start = datetime.datetime(2019, 1, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        homework.save()

        # THEN
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        self.assertEqual(reminder1.start_of_range, datetime.datetime(2019, 5, 8, 11, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertEqual(reminder2.start_of_range, datetime.datetime(2019, 1, 8, 9, 45, 0, tzinfo=datetime.timezone.utc))

    def test_send_window_excludes_stale_reminders(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        beyond_window = timezone.now() - datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES + 1)
        Reminder.objects.filter(pk=reminder.pk).update(start_of_range=beyond_window)

        # THEN
        self.assertNotIn(reminder, Reminder.objects.for_today())

        # WHEN
        within_window = timezone.now() - datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES - 1)
        Reminder.objects.filter(pk=reminder.pk).update(start_of_range=within_window)

        # THEN
        self.assertIn(reminder, Reminder.objects.for_today())

    def test_event_date_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=1)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 11, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)

    def test_event_date_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN
        new_start = datetime.datetime(2016, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2016, 5, 8, 11, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertTrue(reminder.sent)

    def test_event_time_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user,
                                               start=datetime.datetime(2030, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc),
                                               end=datetime.datetime(2030, 5, 8, 14, 0, 0, tzinfo=datetime.timezone.utc))
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 14, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 13, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)

    def test_event_time_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True)

        # WHEN
        new_start = datetime.datetime(2017, 5, 8, 10, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=2)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2017, 5, 8, 9, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertTrue(reminder.sent)

    def test_homework_date_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 16, 0, 0, tzinfo=datetime.timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 15, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)

    def test_homework_date_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN
        new_start = datetime.datetime(2016, 5, 8, 16, 0, 0, tzinfo=datetime.timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2016, 5, 8, 15, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertTrue(reminder.sent)

    def test_homework_time_change_recalculates_start_of_range_within_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=datetime.datetime(2030, 5, 8, 16, 0, 0, tzinfo=datetime.timezone.utc),
                                                        end=datetime.datetime(2030, 5, 8, 18, 0, 0, tzinfo=datetime.timezone.utc))
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 18, 0, 0, tzinfo=datetime.timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 8, 17, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)

    def test_homework_time_change_recalculates_start_of_range_outside_send_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True)

        # WHEN
        new_start = datetime.datetime(2017, 5, 8, 14, 0, 0, tzinfo=datetime.timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range, datetime.datetime(2017, 5, 8, 13, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertTrue(reminder.sent)

