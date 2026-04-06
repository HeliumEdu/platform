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
        course = coursehelper.given_course_exists(course_group,
                                                  start_date=datetime.date.today() - datetime.timedelta(days=7),
                                                  end_date=datetime.date.today() + datetime.timedelta(days=30))
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
        # Course text reminder in the send window — must be excluded (text is legacy; courses are email+push only)
        course_text_reminder = Reminder(
            title='Course reminder', message='Class soon',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.TEXT, sent=False, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([course_text_reminder])
        course_text_reminder = Reminder.objects.get(course=course, sent=False)
        # This reminder is ignored, as we're not yet in its send window
        reminder3 = reminderhelper.given_reminder_exists(user, type=enums.EMAIL, event=event2)
        # Sent reminders are ignored
        reminderhelper.given_reminder_exists(user, sent=True, event=event1)

        # WHEN
        reminderservice.process_text_reminders()

        # THEN — only homework and event reminders are texted; course text reminder is excluded
        self.assertEqual(mock_send_sms.call_count, 2)
        reminder1.refresh_from_db()
        reminder2.refresh_from_db()
        reminder3.refresh_from_db()
        course_text_reminder.refresh_from_db()
        self.assertTrue(reminder1.sent)
        self.assertTrue(reminder2.sent)
        self.assertFalse(reminder3.sent)
        self.assertFalse(course_text_reminder.sent)

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
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1),
                                                end=datetime.datetime.now().replace(
                                                    tzinfo=pytz.timezone(user.settings.time_zone)) + datetime.timedelta(
                                                    days=1, hours=1))
        reminder1 = reminderhelper.given_reminder_exists(user, event=event1, type=enums.PUSH)
        reminder2 = reminderhelper.given_reminder_exists(user, homework=homework, type=enums.PUSH)
        # Course push reminder in the send window — should now be fully pushed (no guard)
        course_reminder = Reminder(
            title='Course reminder', message='Class soon',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False, repeating=True,
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

        # THEN — event, homework, and course all pushed
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

    def test_heal_orphaned_repeating_reminders_deletes_stale_and_creates_successor(self):
        # GIVEN: an unsent reminder whose start_of_range is past the send window (Celery was down
        # during the class; nothing was ever sent or dismissed).
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
            sent=False, dismissed=False, repeating=True, course=course, user=user,
        )
        Reminder.objects.bulk_create([stale])

        # WHEN
        reminderservice.heal_orphaned_repeating_reminders()

        # THEN: stale reminder is deleted and a new occurrence is created for the next class.
        self.assertEqual(Reminder.objects.filter(dismissed=False, sent=False, repeating=True).count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_course_creates_next(self, mock_send_multipart_email):
        # GIVEN: a course email reminder in the send window (repeating)
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
            type=enums.EMAIL, sent=False, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([fired_reminder])

        # WHEN
        reminderservice.process_email_reminders()

        # THEN: original is marked sent; a new pending reminder for the next class is created
        self.assertEqual(Reminder.objects.filter(sent=True).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, repeating=True, course=course).count(), 1)
        self.assertEqual(Reminder.objects.count(), 2)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_excess_past(self, mock_send_notifications):
        # GIVEN: a course push reminder in the send window plus an existing sent+undismissed
        # past reminder for the same series (the user hasn't dismissed it yet).
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
            type=enums.PUSH, sent=True, dismissed=False, repeating=True,
            course=course, user=user,
        )
        pending = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=15, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN: old past is deleted; pending fires and becomes the new past; next occurrence queued.
        # Exactly 2 reminders: 1 sent (just fired) + 1 pending (next class).
        self.assertEqual(Reminder.objects.count(), 2)
        self.assertEqual(Reminder.objects.filter(sent=True, dismissed=False, course=course).count(), 1)
        self.assertEqual(Reminder.objects.filter(sent=False, dismissed=False, course=course).count(), 1)
        # The old_past record must be gone
        self.assertFalse(Reminder.objects.filter(pk=old_past.pk).exists())

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders_auto_deletes_past_with_different_offset(self, mock_send_notifications):
        # GIVEN: a course push reminder fires for the same class after the user edited the offset
        # (e.g. 10 min → 9 min). The previously-sent reminder has offset=10; the re-queued pending
        # reminder has offset=9. The old reminder must be cleaned up even though the offset differs.
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
            type=enums.PUSH, sent=True, dismissed=False, repeating=True,
            course=course, user=user,
        )
        pending = Reminder(
            title='Test', message='Test',
            start_of_range=timezone.now() - datetime.timedelta(minutes=1),
            offset=9, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=False, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([old_past, pending])

        # WHEN
        reminderservice.process_push_reminders()

        # THEN: old past (offset=10) is deleted despite having a different offset; pending (offset=9)
        # fires and becomes the new past; next occurrence queued. Exactly 2 reminders remain.
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
        # GIVEN: an existing sent reminder for a MWF course. After it fires we create the next one.
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

        # THEN: a new pending reminder is created with settings copied from the original
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

    def test_create_next_repeating_reminder_targets_next_class_not_current(self):
        # GIVEN: a course reminder that fired for Monday's class (10:00 AM UTC, offset 30 min).
        # The fired reminder's start_of_range = 09:30 Monday; class_start = 10:00 Monday.
        # create_next_repeating_reminder must use after_datetime=class_start so it skips Monday
        # and targets Wednesday, regardless of when exactly the function is called.
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
        monday_start_of_range = datetime.datetime(2026, 3, 30, 9, 30, 0, tzinfo=pytz.utc)
        reminder = Reminder(
            title='Test', message='Test',
            start_of_range=monday_start_of_range,
            offset=30, offset_type=enums.MINUTES,
            type=enums.PUSH, sent=True, dismissed=False, repeating=True,
            course=course, user=user,
        )
        Reminder.objects.bulk_create([reminder])
        reminder = Reminder.objects.get(course=course)

        # WHEN
        new_reminder = reminderservice.create_next_repeating_reminder(reminder)

        # THEN: next reminder targets Wednesday 2026-04-01 (class at 10:00, start_of_range = 09:30)
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
