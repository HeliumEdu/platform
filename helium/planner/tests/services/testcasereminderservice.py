__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import CourseSchedule, Reminder
from helium.planner.services import reminderservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, homeworkhelper, eventhelper, reminderhelper


class TestCaseReminderService(TestCase):
    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                        end=timezone.now() + datetime.timedelta(minutes=10))
        event1 = eventhelper.given_event_exists(user,
                                                start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                end=timezone.now() + datetime.timedelta(minutes=10))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event1)
        reminder2 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, homework=homework)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, type=enums.EMAIL, sent=True, event=event1)

        # WHEN
        reminderservice.process_email_reminders()

        # THEN
        self.assertEqual(mock_send_multipart_email.call_count, 2)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                        end=timezone.now() + datetime.timedelta(minutes=10))
        event1 = eventhelper.given_event_exists(user,
                                                start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                end=timezone.now() + datetime.timedelta(minutes=10))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=ZoneInfo(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, event=event1, type=enums.PUSH)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework, type=enums.PUSH)
        # Course push reminder in the send window — should now be fully pushed (no guard)
        course_reminder = Reminder(
            title='Course reminder', message='Class soon',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([course_reminder])
        course_reminder = Reminder.objects.get(course=course, sent=False)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.TEXT, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, sent=True, event=event1)

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(mock_send_notifications.call_count, 3)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        course_reminder.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)
        self.assertTrue(course_reminder.sent)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_inactive_user(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event)

        # WHEN
        reminderservice.process_email_reminders()

        # THEN
        # Inactive user should not receive email but reminder should be marked sent
        mock_send_multipart_email.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_no_push_tokens(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        # No push tokens created for user
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event)

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        # No push sent when user has no push tokens
        mock_send_notifications.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_mark_sent_only(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event)

        # WHEN
        reminderservice.process_push_reminders(mark_sent_only=True)

        # THEN
        # No push sent when mark_sent_only=True, but reminder marked as sent
        mock_send_notifications.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    def test_heal_orphaned_repeating_reminders_creates_successor(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminder = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertTrue(Reminder.objects.filter(sent=False, course=course).exists())

    def test_heal_orphaned_repeating_reminders_skips_healthy_series(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        sent_reminder = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=True, dismissed=False,
            course=course, user=user,
        )
        unsent_reminder = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() + datetime.timedelta(days=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([sent_reminder, unsent_reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)

    def test_heal_orphaned_repeating_reminders_deletes_stale_and_creates_successor(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        stale = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=3),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, course=course, user=user,
        )
        Reminder.objects.bulk_create([stale])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN
        self.assertEqual(Reminder.objects.filter(dismissed=False, sent=False).count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_course_creates_next(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        fired_reminder = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.EMAIL, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([fired_reminder])

        # WHEN
        reminderservice.process_email_reminders()

        # THEN
        self.assertEqual(Reminder.objects.filter(sent=True).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.count(), 2)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_excess_past(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        old_past = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(days=2),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        pending = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(Reminder.objects.filter(sent=True, dismissed=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, dismissed=False, course=course).count(), 1)
        # The old_past record must be gone
        self.assertFalse(Reminder.objects.filter(pk=old_past.pk).exists())

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_past_with_different_offset(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='1111111',
                                                          sun_start_time=datetime.time(10, 0, 0),
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          tue_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          thu_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0),
                                                          sat_start_time=datetime.time(10, 0, 0))
        old_past = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=2),
            offset=10, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        pending = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=9, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(Reminder.objects.filter(sent=True, dismissed=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, dismissed=False, course=course).count(), 1)
        self.assertFalse(Reminder.objects.filter(pk=old_past.pk).exists())

    def test_get_subject_orphaned_reminder(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)
        reminder.event = None
        reminder.homework = None
        reminder.course = None

        # WHEN
        subject = reminderservice.get_subject(reminder)

        # THEN
        self.assertIsNone(subject)

    def test_create_next_repeating_reminder_non_repeating(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)

    def test_create_next_repeating_reminder_no_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)

    def test_create_next_repeating_reminder_creates_next_occurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date.today() - datetime.timedelta(days=7),
            end_date=datetime.date.today() + datetime.timedelta(days=30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        reminder = reminderhelper.given_reminder_exists(user, course=course, type=enums.PUSH, sent=True,
                                                        start_of_range=timezone.now() - datetime.timedelta(hours=1))

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(new_reminder.course, course)
        self.assertEqual(new_reminder.user, user)
        self.assertEqual(new_reminder.type, enums.PUSH)
        self.assertTrue(new_reminder.repeating)
        self.assertFalse(new_reminder.sent)
        self.assertIsNotNone(new_reminder.start_of_range)
        # The new reminder must target a class strictly after the one that fired.
        offset_delta = datetime.timedelta(
            **{enums.REMINDER_OFFSET_TYPE_CHOICES[reminder.offset_type][1]: int(reminder.offset)})
        fired_class_start = reminder.start_of_range + offset_delta
        new_class_start = new_reminder.start_of_range + offset_delta
        self.assertGreater(new_class_start, fired_class_start)

    @mock.patch('django.utils.timezone.now')
    def test_create_next_repeating_reminder_targets_next_class_not_current(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 30, 10, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()

        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 3, 23),
            end_date=datetime.date(2026, 4, 30)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        # Monday 2026-03-30 at 09:30 UTC: start_of_range of the fired reminder (class was at 10:00)
        monday_start_of_range = datetime.datetime(2026, 3, 30, 9, 30, 0, tzinfo=datetime.timezone.utc)
        reminder = Reminder(
            title='Test', message='Test',
            start_of_range=monday_start_of_range,
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        expected_start_of_range = datetime.datetime(2026, 4, 1, 9, 30, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(new_reminder.start_of_range, expected_start_of_range)

    @mock.patch('django.utils.timezone.now')
    def test_create_next_repeating_reminder_uses_soonest_of_multiple_schedules_same_day(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 4, 8, 8, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()

        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2026, 3, 23),
            end_date=datetime.date(2026, 4, 30)
        )
        # `CourseSchedule.course` enforces unique=True, so a second schedule can't be persisted
        # for the same course — build it in memory and patch the queryset to simulate it.
        later_schedule = courseschedulehelper.given_course_schedule_exists(
            course, days_of_week='0001000', wed_start_time=datetime.time(14, 0, 0))
        earlier_schedule = CourseSchedule(course=course, days_of_week='0001000',
                                          wed_start_time=datetime.time(9, 0, 0))

        # A reminder that fired just after midnight on Wednesday 2026-03-25, so both the 09:00
        # and 14:00 occurrences later that same day still qualify as "next".
        reminder = Reminder(
            title='Test', message='Test',
            start_of_range=datetime.datetime(2026, 3, 24, 23, 30, 0, tzinfo=datetime.timezone.utc),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        with mock.patch.object(type(course.schedules), 'all', return_value=[later_schedule, earlier_schedule]):
            new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNotNone(new_reminder)
        expected_start_of_range = datetime.datetime(2026, 3, 25, 8, 30, 0, tzinfo=datetime.timezone.utc)
        self.assertEqual(new_reminder.start_of_range, expected_start_of_range)

    @mock.patch('django.utils.timezone.now')
    def test_get_next_course_occurrence_start_resolves_cycle_day(self, mock_now):
        # GIVEN
        mock_now.return_value = datetime.datetime(2026, 3, 3, 8, 0, 0, tzinfo=datetime.timezone.utc)
        user = userhelper.given_a_user_exists()
        user.settings.time_zone = 'UTC'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(
            course_group, start_date=datetime.date(2026, 3, 2), end_date=datetime.date(2026, 3, 31))
        courseschedulehelper.given_cycle_schedule_exists(
            course, cycle_length=2, anchor_date=datetime.date(2026, 3, 2),
            cycle_slots=[{'indices': [1], 'start_time': '09:00:00', 'end_time': '09:50:00'}])
        reminder = Reminder(course=course, user=user, offset=30, offset_type=enums.MINUTES, type=enums.PUSH)

        # WHEN
        next_start = reminder._get_next_course_occurrence_start()

        # THEN - "now" is Tue 03-03 (Day 2, no meeting); the next Day 1 meeting is Wed 03-04 at 09:00
        self.assertEqual(next_start, datetime.datetime(2026, 3, 4, 9, 0, 0, tzinfo=datetime.timezone.utc))

    def test_create_next_repeating_reminder_no_future_occurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        # Course that has already ended
        course = coursehelper.given_course_exists(
            course_group,
            start_date=datetime.date(2020, 1, 6),
            end_date=datetime.date(2020, 5, 8)
        )
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010',
                                                          mon_start_time=datetime.time(10, 0, 0),
                                                          wed_start_time=datetime.time(10, 0, 0),
                                                          fri_start_time=datetime.time(10, 0, 0))
        # Manually build a reminder bypassing save() since the course has no future occurrence
        reminder = Reminder(
            title='Test',
            message='Test',
            start_of_range=datetime.datetime(2020, 5, 4, 9, 30, tzinfo=datetime.timezone.utc),
            offset=30,
            offset_type=enums.MINUTES,
            type=enums.PUSH,
            course=course,
            user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)
        self.assertEqual(Reminder.objects.count(), 1)

    def test_clone_reminders_rejects_course_source(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN / THEN
        with self.assertRaises(ValueError):
            reminderservice.clone_reminders(course, homework)
        with self.assertRaises(ValueError):
            reminderservice.clone_reminders(homework, course)
