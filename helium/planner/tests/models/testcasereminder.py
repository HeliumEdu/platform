import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import IntegrityError
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


    def test_event_date_change_within_send_window_rearms_dismissed_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True, dismissed=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=1)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range,
                         datetime.datetime(2030, 5, 8, 11, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)
        self.assertFalse(reminder.dismissed)

    def test_homework_date_change_within_send_window_rearms_dismissed_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        reminder = reminderhelper.given_reminder_exists(user, homework=homework, sent=True, dismissed=True)

        # WHEN
        new_start = datetime.datetime(2030, 5, 8, 16, 0, 0, tzinfo=datetime.timezone.utc)
        homework.start = new_start
        homework.end = new_start + datetime.timedelta(hours=2)
        homework.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range,
                         datetime.datetime(2030, 5, 8, 15, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertFalse(reminder.sent)
        self.assertFalse(reminder.dismissed)

    def test_event_date_change_outside_send_window_leaves_dismissed_reminder_alone(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True, dismissed=True)

        # WHEN
        new_start = datetime.datetime(2017, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=1)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertEqual(reminder.start_of_range,
                         datetime.datetime(2017, 5, 8, 11, 45, 0, tzinfo=datetime.timezone.utc))
        self.assertTrue(reminder.sent)
        self.assertTrue(reminder.dismissed)

    def test_rearmed_dismissed_reminder_becomes_sendable_again(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, sent=True, dismissed=True)

        # WHEN
        new_start = timezone.now() + datetime.timedelta(minutes=15)
        event.start = new_start
        event.end = new_start + datetime.timedelta(hours=1)
        event.save()

        # THEN
        reminder.refresh_from_db()
        self.assertIn(reminder, Reminder.objects.active())
        self.assertIn(reminder, Reminder.objects.unsent().for_today())

    def test_active_course_series_is_unique_at_the_database(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        reminderhelper.given_reminder_exists(user, course=course, offset=30,
                                              start_of_range=timezone.now())

        # WHEN / THEN
        with self.assertRaises(IntegrityError):
            reminderhelper.given_reminder_exists(user, course=course, offset=30,
                                                  start_of_range=timezone.now())

    def test_sent_course_reminders_do_not_occupy_the_active_series_slot(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        past = reminderhelper.given_reminder_exists(user, course=course, offset=30, sent=True,
                                                     start_of_range=timezone.now())
        dismissed = reminderhelper.given_reminder_exists(user, course=course, offset=30, sent=True,
                                                          dismissed=True,
                                                          start_of_range=timezone.now())

        # WHEN
        active = reminderhelper.given_reminder_exists(user, course=course, offset=30,
                                                       start_of_range=timezone.now())

        # THEN
        past.refresh_from_db()
        dismissed.refresh_from_db()
        active.refresh_from_db()
        self.assertIsNone(past.active_course_series)
        self.assertIsNone(dismissed.active_course_series)
        self.assertEqual(active.active_course_series, course.pk)


class TestCaseRecurringEventReminder(TestCase):
    @mock.patch('django.utils.timezone.now')
    def test_unsent_reminder_tracks_the_next_upcoming_occurrence(self, mock_now):
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        for zone, expected in (('Europe/Amsterdam', datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc)),
                               ('America/Los_Angeles', datetime.datetime(2030, 5, 6, 15, 30, tzinfo=datetime.timezone.utc))):
            with self.subTest(zone=zone):
                # GIVEN
                user = userhelper.given_a_user_exists(username=zone, email=f'{zone.replace("/", "")}@test.com',
                                                      time_zone=zone)
                event = eventhelper.given_weekly_event_exists(user)

                # WHEN
                reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30)

                # THEN
                self.assertEqual(reminder.start_of_range, expected)
                self.assertFalse(reminder.sent)

    @mock.patch('django.utils.timezone.now')
    def test_unsent_reminder_skips_an_excluded_occurrence(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user, exception_dates=['2030-05-06T07:00:00Z'])

        # WHEN
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30)

        # THEN
        self.assertEqual(reminder.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))

    @mock.patch('django.utils.timezone.now')
    def test_sent_reminder_keeps_the_occurrence_it_fired_for_when_the_series_moves(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 7, 30, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        fired_at = datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc)
        fired = reminderhelper.given_reminder_exists(user, event=event, offset=30, sent=True,
                                                      start_of_range=fired_at)

        # WHEN
        event.start += datetime.timedelta(hours=2)
        event.end += datetime.timedelta(hours=2)
        event.save()
        fired.save()

        # THEN
        fired.refresh_from_db()
        self.assertTrue(fired.sent)
        self.assertEqual(fired.start_of_range, fired_at)

    @mock.patch('django.utils.timezone.now')
    def test_unsent_reminder_on_an_ended_series_falls_back_to_the_series_start(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        start = datetime.datetime(2030, 4, 1, 9, 0, tzinfo=ZoneInfo('Europe/Amsterdam'))
        event = eventhelper.given_weekly_event_exists(user, start=start, recurrence_rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2')

        # WHEN
        reminder = reminderhelper.given_reminder_exists(user, event=event, offset=30)

        # THEN
        self.assertEqual(reminder.start_of_range, start - datetime.timedelta(minutes=30))
        self.assertFalse(reminder.sent)

    @mock.patch('django.utils.timezone.now')
    def test_editing_the_series_in_the_send_window_never_rearms_the_occurrence_that_fired(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2030, 5, 6, 6, 40, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        event = eventhelper.given_weekly_event_exists(user)
        reminderhelper.given_reminder_exists(
            user, event=event, offset=30, sent=True,
            start_of_range=datetime.datetime(2030, 5, 6, 6, 30, tzinfo=datetime.timezone.utc))
        successor = reminderhelper.given_reminder_exists(user, event=event, offset=30)

        # WHEN
        event.title = 'Renamed'
        event.save()
        successor.save()

        # THEN
        successor.refresh_from_db()
        self.assertEqual(successor.start_of_range, datetime.datetime(2030, 5, 13, 6, 30, tzinfo=datetime.timezone.utc))
