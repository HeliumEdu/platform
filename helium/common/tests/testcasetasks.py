__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import TestCase, override_settings

from helium.common.tasks import send_text, send_pushes


class TestCaseTasks(TestCase):
    @override_settings(DISABLE_TEXTS=True)
    @mock.patch('helium.common.tasks.send_sms')
    @mock.patch('helium.common.tasks.metricutils.task_stop')
    @mock.patch('helium.common.tasks.metricutils.task_start')
    @mock.patch('helium.common.tasks.metricutils.get_published_at_ms')
    def test_send_text_disabled(self, mock_published, mock_start, mock_stop, mock_send_sms):
        # GIVEN
        mock_published.return_value = 12345
        mock_start.return_value = {'start': 'metrics'}

        # WHEN
        send_text('+15551234567', 'Test message')

        # THEN
        mock_send_sms.assert_not_called()
        mock_stop.assert_called_once_with({'start': 'metrics'}, value=0)

    @override_settings(DISABLE_TEXTS=False)
    @mock.patch('helium.common.tasks.send_sms')
    @mock.patch('helium.common.tasks.metricutils.task_stop')
    @mock.patch('helium.common.tasks.metricutils.task_start')
    @mock.patch('helium.common.tasks.metricutils.get_published_at_ms')
    def test_send_text_enabled(self, mock_published, mock_start, mock_stop, mock_send_sms):
        # GIVEN
        mock_published.return_value = 12345
        mock_start.return_value = {'start': 'metrics'}

        # WHEN
        send_text('+15551234567', 'Test message')

        # THEN
        mock_send_sms.assert_called_once_with('+15551234567', 'Test message')
        mock_stop.assert_called_once_with({'start': 'metrics'})

    @override_settings(DISABLE_PUSH=True)
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('helium.common.tasks.metricutils.task_stop')
    @mock.patch('helium.common.tasks.metricutils.task_start')
    @mock.patch('helium.common.tasks.metricutils.get_published_at_ms')
    def test_send_pushes_disabled(self, mock_published, mock_start, mock_stop, mock_send_notifications):
        # GIVEN
        mock_published.return_value = 12345
        mock_start.return_value = {'start': 'metrics'}
        reminder_data = {'id': 1}

        # WHEN
        send_pushes(['token1'], 'user1', 'Subject', 'Message', reminder_data)

        # THEN
        mock_send_notifications.assert_not_called()
        mock_stop.assert_called_once_with({'start': 'metrics'}, value=0)

    @override_settings(DISABLE_PUSH=False)
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('helium.common.tasks.metricutils.task_stop')
    @mock.patch('helium.common.tasks.metricutils.task_start')
    @mock.patch('helium.common.tasks.metricutils.get_published_at_ms')
    def test_send_pushes_enabled(self, mock_published, mock_start, mock_stop, mock_send_notifications):
        # GIVEN
        mock_published.return_value = 12345
        mock_start.return_value = {'start': 'metrics'}
        reminder_data = {'id': 1}

        # WHEN
        send_pushes(['token1'], 'user1', 'Subject', 'Message', reminder_data)

        # THEN
        mock_send_notifications.assert_called_once_with(['token1'], 'Subject', 'Message', reminder_data)
        mock_stop.assert_called_once_with({'start': 'metrics'})
