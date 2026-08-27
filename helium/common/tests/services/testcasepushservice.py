from unittest import mock

from django.test import TestCase
from firebase_admin import exceptions as firebase_exceptions
from firebase_admin import messaging

from helium.common.services import pushservice


def given_send_response(*failures):
    """Build a BatchResponse whose per-token results carry the given exceptions, one per token,
    with None standing in for a successful send."""
    responses = []
    for exception in failures:
        response = mock.MagicMock()
        response.success = exception is None
        response.exception = exception
        responses.append(response)

    batch = mock.MagicMock()
    batch.responses = responses
    batch.success_count = sum(1 for e in failures if e is None)
    batch.failure_count = sum(1 for e in failures if e is not None)

    return batch


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
        self.assertEqual(mock_increment.call_count, 2)
        mock_increment.assert_any_call('action.push.sent', value=2)
        mock_increment.assert_any_call('action.reminder.sent', value=2, extra_tags=['channel:push'])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_partial_failure(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(None, messaging.UnregisteredError('gone'))
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1}

        # WHEN
        pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        # THEN
        self.assertEqual(mock_increment.call_count, 2)
        mock_increment.assert_any_call('action.push.sent', value=1)
        mock_increment.assert_any_call('action.reminder.sent', value=1, extra_tags=['channel:push'])
        failed = [c for c in mock_increment.call_args_list if c.args[0] == 'action.push.failed']
        self.assertEqual(failed, [])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_all_failed(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(messaging.UnregisteredError('gone'),
                                                     messaging.ThirdPartyAuthError('apns key rejected'))
        push_tokens = ['token1', 'token2']
        reminder_data = {'id': 1}

        # WHEN
        pushservice.send_notifications(push_tokens, 'Subject', 'Message', reminder_data)

        # THEN
        self.assertEqual(mock_increment.call_count, 1)
        mock_increment.assert_any_call('action.push.failed', value=1,
                                       extra_tags=['reason:third_party_auth', 'operation:notification'])

    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_uses_platform_specific_notification_fields(self, mock_send):
        # GIVEN
        mock_response = mock.MagicMock()
        mock_response.success_count = 1
        mock_response.failure_count = 0
        mock_send.return_value = mock_response

        # WHEN
        pushservice.send_notifications(['token1'], 'Subject', 'Message', {'id': 1})

        # THEN
        message = mock_send.call_args[0][0]
        self.assertIsNone(message.notification)

        # AND: native platforms receive notification via platform-specific configs
        self.assertEqual(message.android.notification.title, 'Subject')
        self.assertEqual(message.android.notification.body, 'Message')
        self.assertEqual(message.apns.payload.aps.alert.title, 'Subject')
        self.assertEqual(message.apns.payload.aps.alert.body, 'Message')
        self.assertIsNone(message.apns.payload.aps.content_available)

        # AND: json_payload includes notification_title/body for web clients (no message.notification)
        import json
        payload = json.loads(message.data['json_payload'])
        self.assertEqual(payload['notification_title'], 'Subject')
        self.assertEqual(payload['notification_body'], 'Message')

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

        mock_increment.assert_called_once_with('action.push.failed', value=2,
                                               extra_tags=['reason:request_failed', 'operation:notification'])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_groups_repeated_reasons(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(messaging.UnregisteredError('gone'),
                                                     messaging.UnregisteredError('gone'),
                                                     messaging.QuotaExceededError('slow down'))

        # WHEN
        pushservice.send_notifications(['t1', 't2', 't3'], 'Subject', 'Message', {'id': 1})

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args[0] == 'action.push.failed']
        self.assertEqual(len(failed), 1)
        mock_increment.assert_any_call('action.push.failed', value=1,
                                       extra_tags=['reason:quota_exceeded', 'operation:notification'])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_returns_only_permanently_invalid_tokens(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(messaging.UnregisteredError('gone'),
                                                     messaging.ThirdPartyAuthError('apns key rejected'),
                                                     messaging.SenderIdMismatchError('wrong project'))

        # WHEN
        invalid = pushservice.send_notifications(['t1', 't2', 't3'], 'Subject', 'Message', {'id': 1})

        # THEN
        self.assertEqual(invalid, ['t1', 't3'])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_falls_back_to_the_firebase_error_code(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(firebase_exceptions.UnavailableError('fcm is down'),
                                                     firebase_exceptions.InvalidArgumentError('bad payload'))

        # WHEN
        pushservice.send_notifications(['t1', 't2'], 'Subject', 'Message', {'id': 1})

        # THEN
        mock_increment.assert_any_call('action.push.failed', value=1, extra_tags=['reason:unavailable', 'operation:notification'])
        mock_increment.assert_any_call('action.push.failed', value=1, extra_tags=['reason:invalid_argument', 'operation:notification'])

    @mock.patch('helium.common.services.pushservice.metricutils.increment')
    @mock.patch('helium.common.services.pushservice.messaging.send_each_for_multicast')
    def test_send_notifications_reasons_non_firebase_failures_as_unknown(self, mock_send, mock_increment):
        # GIVEN
        mock_send.return_value = given_send_response(ValueError('something else entirely'))

        # WHEN
        pushservice.send_notifications(['t1'], 'Subject', 'Message', {'id': 1})

        # THEN
        mock_increment.assert_any_call('action.push.failed', value=1, extra_tags=['reason:unknown', 'operation:notification'])

