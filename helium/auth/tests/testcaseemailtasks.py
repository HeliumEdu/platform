from unittest import mock

from django.conf import settings
from django.test import TestCase, override_settings

from helium.auth.tasks import send_dormant_user_warning_email, send_password_reset_email, \
    send_registration_email, send_verification_email
from helium.auth.tests.helpers import userhelper
from helium.common.tests.helpers import commonhelper
from helium.common import enums
from helium.planner.tasks import email_reminders
from helium.planner.tests.helpers import reminderhelper


@override_settings(DISABLE_EMAILS=False)
class TestCaseEmailTasks(TestCase):
    @mock.patch('helium.auth.tasks.clear_ses_suppression_if_exists')
    @mock.patch('helium.auth.tasks.commonutils.send_multipart_email')
    def test_account_emails_are_sent_in_the_accounts_language(self, mock_send, mock_clear):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send)
        user = userhelper.given_a_user_exists()
        user.settings.language = 'es'
        user.settings.save()

        # WHEN
        send_verification_email(user.email, 123456)
        send_registration_email(user.email)
        send_password_reset_email(user.email, 'https://app.heliumedu.com/reset')

        # THEN
        self.assertEqual(sent, [
            ('email/verification', 'Verify Your Email Address with Helium', 'es'),
            ('email/register', 'Welcome to Helium', 'es'),
            ('email/forgot', 'Reset Your Helium Password', 'es'),
        ])

    @mock.patch('helium.auth.tasks.clear_ses_suppression_if_exists')
    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    @mock.patch('helium.auth.tasks.commonutils.send_multipart_email')
    def test_emails_to_an_account_with_the_default_language_are_english(self, mock_send, mock_send_reminder,
                                                                          mock_clear):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send, mock_send_reminder)
        user = userhelper.given_a_user_exists()
        reminderhelper.given_due_reminder_exists(user, enums.EMAIL)

        # WHEN
        send_verification_email(user.email, 123456)
        send_registration_email(user.email)
        send_password_reset_email(user.email, 'https://app.heliumedu.com/reset')
        send_dormant_user_warning_email(user.pk)
        email_reminders()

        # THEN
        self.assertEqual([language for _, _, language in sent], ['en'] * 5)

    @mock.patch('helium.auth.tasks.commonutils.send_multipart_email')
    def test_verification_email_for_an_email_change_uses_the_accounts_language(self, mock_send):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send)
        user = userhelper.given_a_user_exists()
        user.email_changing = 'new@test.com'
        user.save()
        user.settings.language = 'es'
        user.settings.save()

        # WHEN
        send_verification_email('new@test.com', 123456)

        # THEN
        self.assertEqual(sent[0][2], 'es')

    @mock.patch('helium.auth.tasks.commonutils.send_multipart_email')
    def test_email_to_an_unknown_address_is_english(self, mock_send):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send)

        # WHEN
        send_verification_email('nobody@test.com', 123456)

        # THEN
        self.assertEqual(sent[0][2], 'en')

    @mock.patch('helium.auth.tasks.commonutils.send_multipart_email')
    def test_dormant_warning_subjects(self, mock_send):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send)
        user = userhelper.given_a_user_exists()
        user.settings.language = 'es'
        user.settings.save()

        # WHEN
        for _ in settings.DORMANT_USER_WARNING_DAYS:
            send_dormant_user_warning_email(user.pk)

        # THEN
        self.assertEqual([(subject, language) for _, subject, language in sent], [
            ('Your Account Will Be Deleted in 30 Days', 'es'),
            ('Reminder: 14 Days Until Account Deletion', 'es'),
            ('Reminder: Only 7 Days Left', 'es'),
            ('Final Notice: Account Deletion Tomorrow', 'es'),
        ])

    @mock.patch('helium.planner.tasks.commonutils.send_multipart_email')
    def test_reminder_email_is_sent_in_the_users_language(self, mock_send):
        # GIVEN
        sent = commonhelper.given_sent_emails_are_recorded(mock_send)
        user = userhelper.given_a_user_exists()
        user.settings.language = 'es'
        user.settings.save()
        reminderhelper.given_due_reminder_exists(user, enums.EMAIL)

        # WHEN
        email_reminders()

        # THEN
        self.assertEqual(sent, [('email/reminder', '🏀 Test Event in 15 minutes', 'es')])
