__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from unittest import mock

from django.test import TestCase

from helium.planner.tasks import email_reminders, text_reminders


class TestCasePlannerTasks(TestCase):
    @mock.patch('helium.planner.services.reminderservice.process_email_reminders')
    def test_email_reminders(self, mock_process_email_reminders):
        # WHEN
        email_reminders()

        # THEN
        mock_process_email_reminders.assert_called_once()

    @mock.patch('helium.planner.services.reminderservice.process_text_reminders')
    def test_text_reminders(self, mock_process_text_reminders):
        # WHEN
        text_reminders()

        # THEN
        mock_process_text_reminders.assert_called_once()
