__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
from unittest import mock

import pytz
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Reminder
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
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
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

    @mock.patch('helium.common.tasks.send_sms')
    def test_process_text_reminders(self, mock_send_sms):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.profile.phone = '5555555'
        user.profile.phone_verified = True
        user.profile.save()
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
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, event=event1)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, sent=True, event=event1)

        # WHEN
        reminderservice.process_text_reminders()

        # THEN
        self.assertEqual(mock_send_sms.call_count, 2)
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
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course,
                                                        start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                        end=timezone.now() + datetime.timedelta(minutes=10))
        event1 = eventhelper.given_event_exists(user,
                                                start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                                end=timezone.now() + datetime.timedelta(minutes=10))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime.now().replace(
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, event=event1, type=enums.PUSH)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework, type=enums.PUSH)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.TEXT, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, sent=True, event=event1)

        # WHEN
        reminderservice.process_push_reminders()

        # THEN
        self.assertEqual(mock_send_notifications.call_count, 2)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)

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

    @mock.patch('helium.common.tasks.send_sms')
    def test_process_text_reminders_no_phone(self, mock_send_sms):
        # GIVEN
        user = userhelper.given_a_user_exists()
        # User has no phone set (default)
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.TEXT, event=event)

        # WHEN
        reminderservice.process_text_reminders()

        # THEN
        # No SMS sent when user has no phone
        mock_send_sms.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)

    @mock.patch('helium.common.tasks.send_sms')
    def test_process_text_reminders_phone_not_verified(self, mock_send_sms):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.profile.phone = '5555555'
        user.profile.phone_verified = False  # Phone not verified
        user.profile.save()
        event = eventhelper.given_event_exists(user,
                                               start=timezone.now() + datetime.timedelta(minutes=settings.REMINDER_SEND_WINDOW_MINUTES),
                                               end=timezone.now() + datetime.timedelta(minutes=10))
        reminder = reminderhelper.given_reminder_exists(user, type=enums.TEXT, event=event)

        # WHEN
        reminderservice.process_text_reminders()

        # THEN
        # No SMS sent when phone not verified
        mock_send_sms.assert_not_called()
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
        # GIVEN: a sent repeating course reminder with no unsent successor (orphaned series)
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
            sent=True, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN: next occurrence is created, original remains unchanged
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertTrue(Reminder.objects.filter(sent=False, repeating=True, course=course).exists())

    def test_heal_orphaned_repeating_reminders_skips_healthy_series(self):
        # GIVEN: a sent repeating reminder that already has an unsent successor (healthy series)
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
            sent=True, dismissed=False, repeating=True,
            course=course, user=user,
        )
        unsent_reminder = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() + datetime.timedelta(days=2),
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=False, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([sent_reminder, unsent_reminder])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN: no new reminders created, healthy series left untouched
        self.assertEqual(Reminder.objects.count(), 2)

    def test_heal_orphaned_repeating_reminders_dismisses_duplicate_undismissed(self):
        # GIVEN: three undismissed repeating reminders for the same series (the duplication bug scenario);
        # none are stale — the most recent is in the future, so it should be kept active.
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
        older = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        duplicate = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        most_recent = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() + datetime.timedelta(days=2),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        Reminder.objects.bulk_create([older, duplicate, most_recent])
        most_recent_pk = Reminder.objects.order_by('-start_of_range').first().pk

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN: only the most recent remains active; the two older duplicates are dismissed;
        # no new occurrence is created because the most recent is still valid.
        self.assertEqual(Reminder.objects.filter(dismissed=False).count(), 1)
        self.assertEqual(Reminder.objects.filter(dismissed=False).first().pk, most_recent_pk)
        self.assertEqual(Reminder.objects.count(), 3)

    def test_heal_orphaned_repeating_reminders_dismisses_all_stale_and_creates_successor(self):
        # GIVEN: multiple undismissed reminders for the same series, all with start_of_range past
        # the send window (the class already happened and nothing was ever sent or dismissed).
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
        stale_1 = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=3),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        stale_2 = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(hours=2),
            offset=30, offset_type=enums.MINUTES, type=enums.PUSH,
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        Reminder.objects.bulk_create([stale_1, stale_2])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN: both stale reminders are dismissed and a new occurrence is created for the next class.
        self.assertEqual(Reminder.objects.filter(dismissed=True).count(), 2)
        self.assertEqual(Reminder.objects.filter(dismissed=False, sent=False, repeating=True).count(), 1)

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
        reminder = reminderhelper.given_reminder_exists(user, event=event, repeating=False)

        # WHEN
        result = reminderservice.create_next_repeating_reminder(reminder)

        # THEN
        self.assertIsNone(result)

    def test_create_next_repeating_reminder_no_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, event=event, repeating=True)

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
        reminder = reminderhelper.given_reminder_exists(user, course=course, repeating=True, type=enums.PUSH)

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

    @mock.patch('helium.planner.models.reminder.datetime')
    def test_create_next_repeating_reminder_skips_occurrence_outside_send_window(self, mock_datetime):
        # GIVEN
        # Freeze "now" to Monday 2026-03-30 09:58 UTC. Course meets M/W/F at 10:00 AM UTC.
        # Offset = 30 min → Monday start_of_range = 09:30 UTC.
        # window_start = 09:58 - 15min = 09:43 UTC. 09:30 < 09:43 → Monday is outside the window.
        # Wednesday start_of_range = 09:30 Apr 1 UTC, which is beyond Monday's window_start → valid.
        frozen_now = datetime.datetime(2026, 3, 30, 9, 58, 0, tzinfo=pytz.utc)
        mock_datetime.datetime.now.return_value = frozen_now
        mock_datetime.datetime.combine = datetime.datetime.combine
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.date = datetime.date

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
        reminder = Reminder(
            title='Test',
            message='Test',
            start_of_range=frozen_now,
            offset=30,
            offset_type=enums.MINUTES,
            type=enums.PUSH,
            sent=True,
            dismissed=False,
            repeating=True,
            course=course,
            user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN - Wednesday's occurrence is returned, Monday's is skipped (its window has passed)
        self.assertIsNotNone(new_reminder)
        expected_start_of_range = datetime.datetime(2026, 4, 1, 9, 30, 0, tzinfo=pytz.utc)
        self.assertEqual(new_reminder.start_of_range, expected_start_of_range)

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
            start_of_range=datetime.datetime(2020, 5, 4, 9, 30, tzinfo=pytz.utc),
            offset=30,
            offset_type=enums.MINUTES,
            type=enums.PUSH,
            repeating=True,
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
