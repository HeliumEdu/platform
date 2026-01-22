__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.35"

import datetime
from unittest import mock

import pytz
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.services import reminderservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, eventhelper, reminderhelper


class TestCaseReminderService(TestCase):
    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_a_user_exists()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        event1 = eventhelper.given_event_exists(user)
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
        self.assertTrue(reminder3.sent)

    @mock.patch('helium.common.tasks.send_sms')
    def test_process_text_reminders(self, mock_send_sms):
        # GIVEN
        user = userhelper.given_a_user_exists()
        user.profile.phone = '5555555'
        user.profile.phone_verified = True
        user.profile.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        event1 = eventhelper.given_event_exists(user)
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
        self.assertTrue(reminder3.sent)

    @mock.patch('helium.common.tasks.send_notifications')
    def test_process_push_reminders(self, mock_send_notifications):
        # GIVEN
        user = userhelper.given_a_user_exists()
        userhelper.given_user_push_token_exists(user)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        event1 = eventhelper.given_event_exists(user)
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
        self.assertTrue(reminder3.sent)

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_process_email_reminders_inactive_user(self, mock_send_multipart_email):
        # GIVEN
        user = userhelper.given_an_inactive_user_exists()
        event = eventhelper.given_event_exists(user)
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
        event = eventhelper.given_event_exists(user)
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
        event = eventhelper.given_event_exists(user)
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
        event = eventhelper.given_event_exists(user)
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
        event = eventhelper.given_event_exists(user)
        reminder = reminderhelper.given_reminder_exists(user, type=enums.PUSH, event=event)

        # WHEN
        reminderservice.process_push_reminders(mark_sent_only=True)

        # THEN
        # No push sent when mark_sent_only=True, but reminder marked as sent
        mock_send_notifications.assert_not_called()
        reminder.refresh_from_db()
        self.assertTrue(reminder.sent)