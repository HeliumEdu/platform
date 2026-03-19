__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import TestCase

from helium.common.services import pushservice


class TestCasePushService(TestCase):
    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_success(self, mock_send, mock_increment):
        # GIVEN
        mock_response = mock.MagicMock()
        mock_response.success_count = 2
        mock_response.failure_count = 0
        mock_send.return_value = mock_response
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1, 'title': 'Test'}

        # WHEN
        pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        # THEN
        mock_send.assert_called_once()
        mock_increment.assert_called_once_with('action.push.sent', value=2)

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_partial_failure(self, mock_send, mock_increment):
        # GIVEN
        mock_response = mock.MagicMock()
        mock_response.success_count = 1
        mock_response.failure_count = 1
        mock_send.return_value = mock_response
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1}

        # WHEN
        pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        # THEN
        self.assertEqual(mock_increment.call_count, 2)
        mock_increment.assert_any_call('action.push.sent', value=1)
        mock_increment.assert_any_call('action.push.failed', value=1)

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_all_failed(self, mock_send, mock_increment):
        # GIVEN
        mock_response = mock.MagicMock()
        mock_response.success_count = 0
        mock_response.failure_count = 2
        mock_send.return_value = mock_response
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1}

        # WHEN
        pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        # THEN
        mock_increment.assert_called_once_with('action.push.failed', value=2)

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_exception(self, mock_send, mock_increment):
        # GIVEN
        mock_send.side_effect = Exception('Firebase error')
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1}

        # WHEN/THEN
        with self.assertRaises(Exception):
            pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        mock_increment.assert_called_once_with('action.push.failed', value=2)
