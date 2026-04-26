__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import urllib.error
from unittest import mock

from django.test import TestCase, override_settings

from helium.auth.tests.helpers import userhelper
from helium.common.services import analyticsservice


@override_settings(GA4_MEASUREMENT_ID='G-TEST', GA4_API_SECRET='secret')
class TestCaseAnalyticsService(TestCase):
    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_success(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists()
        mock_response = mock.MagicMock()
        mock_response.status = 204
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete',
                                    user_properties={'onboarding_duration_seconds': 42})

        # THEN
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertIn('measurement_id=G-TEST', request.full_url)
        self.assertIn('api_secret=secret', request.full_url)
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(payload['client_id'], f'server-{user.pk}')
        self.assertEqual(payload['user_id'], str(user.pk))
        self.assertEqual(payload['events'][0]['name'], 'helium_onboarding_complete')
        self.assertEqual(payload['events'][0]['params'], {})
        self.assertEqual(payload['user_properties'],
                         {'onboarding_duration_seconds': {'value': 42}})
        mock_increment.assert_called_once_with('action.analytics.sent')

    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_unexpected_status(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists()
        mock_response = mock.MagicMock()
        mock_response.status = 500
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        # THEN
        mock_increment.assert_called_once_with('action.analytics.unexpected_status')

    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_network_error_is_swallowed(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists()
        mock_urlopen.side_effect = urllib.error.URLError('timeout')

        # WHEN/THEN: does not raise
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        mock_increment.assert_called_once_with('action.analytics.failed')

    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_skips_heliumedu_com_user(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists(email='admin@heliumedu.com')

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        # THEN
        mock_urlopen.assert_not_called()
        mock_increment.assert_not_called()

    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_skips_heliumedu_dev_user(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists(email='dev@heliumedu.dev')

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        # THEN
        mock_urlopen.assert_not_called()
        mock_increment.assert_not_called()

    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_skips_superuser(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists(email='outside@example.com')
        user.is_superuser = True
        user.save(update_fields=['is_superuser'])

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        # THEN
        mock_urlopen.assert_not_called()
        mock_increment.assert_not_called()

    @override_settings(GA4_MEASUREMENT_ID=None, GA4_API_SECRET=None)
    @mock.patch('helium.common.services.analyticsservice.metricutils.increment')
    @mock.patch('helium.common.services.analyticsservice.urllib.request.urlopen')
    def test_send_event_noop_when_not_configured(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists()

        # WHEN
        analyticsservice.send_event(user, 'helium_onboarding_complete')

        # THEN
        mock_urlopen.assert_not_called()
        mock_increment.assert_not_called()
