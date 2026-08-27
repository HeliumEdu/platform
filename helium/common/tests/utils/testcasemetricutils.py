from unittest import mock

from django.test import SimpleTestCase

from helium.common.utils import metricutils
from helium.common.utils.metricutils import _client_tags

DART_APP = 'Dart/3.5 (dart:io)'
IOS_BROWSER = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
               'Safari/604.1')
ANDROID_BROWSER = ('Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 Chrome/120.0 '
                   'Mobile Safari/537.36')
DESKTOP_BROWSER = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                   'Chrome/120.0 Safari/537.36')
CRAWLER = 'Googlebot/2.1 (+http://www.google.com/bot.html)'


def _request(client_platform=None, user_agent=None):
    headers = {}
    if client_platform is not None:
        headers['X-Client-Platform'] = client_platform
    if user_agent is not None:
        headers['User-Agent'] = user_agent

    request = mock.Mock()
    request.headers = headers
    return request


class TestCaseMetricUtils(SimpleTestCase):
    def test_client_tags_splits_app_by_ios(self):
        # GIVEN
        request = _request(client_platform='ios', user_agent=DART_APP)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:app', tags)
        self.assertIn('client_os:ios', tags)

    def test_client_tags_splits_app_by_android(self):
        # GIVEN
        request = _request(client_platform='android', user_agent=DART_APP)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:app', tags)
        self.assertIn('client_os:android', tags)

    def test_client_tags_resolves_desktop_browser(self):
        # GIVEN
        request = _request(client_platform='web', user_agent=DESKTOP_BROWSER)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:web', tags)
        self.assertIn('client_os:desktop', tags)

    def test_client_tags_resolves_mobile_browser_os_from_user_agent(self):
        # GIVEN
        request = _request(client_platform='web', user_agent=IOS_BROWSER)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:web', tags)
        self.assertIn('client_os:ios', tags)

    def test_client_tags_falls_back_to_app_without_header(self):
        # GIVEN
        request = _request(user_agent=DART_APP)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:app', tags)
        self.assertIn('client_os:other', tags)

    def test_client_tags_falls_back_to_browser_os_without_header(self):
        # GIVEN
        request = _request(user_agent=ANDROID_BROWSER)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:web', tags)
        self.assertIn('client_os:android', tags)

    def test_client_tags_separates_bots_from_web(self):
        # GIVEN
        request = _request(user_agent=CRAWLER)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:bot', tags)
        self.assertIn('client_os:other', tags)

    def test_client_tags_ignores_header_casing(self):
        # GIVEN
        request = _request(client_platform='IOS', user_agent=DART_APP)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:app', tags)
        self.assertIn('client_os:ios', tags)

    def test_client_tags_falls_back_when_header_unrecognized(self):
        # GIVEN
        request = _request(client_platform='windows', user_agent=DESKTOP_BROWSER)

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('client:web', tags)
        self.assertIn('client_os:desktop', tags)

    def test_client_tags_defaults_to_other_without_user_agent(self):
        # GIVEN
        request = _request()

        # WHEN
        tags = _client_tags(request)

        # THEN
        self.assertIn('user_agent:unknown', tags)
        self.assertIn('client:other', tags)
        self.assertIn('client_os:other', tags)


class TestCaseTaskFailureMetrics(SimpleTestCase):
    @mock.patch('helium.common.utils.metricutils.task_stop')
    @mock.patch('helium.common.utils.metricutils.increment')
    def test_task_failure_closes_out_timing_when_given_metrics(self, mock_increment, mock_task_stop):
        # GIVEN
        metrics = metricutils.task_start('some.task', priority='low')

        # WHEN
        metricutils.task_failure('some.task', exception_type='ValueError', metrics=metrics)

        # THEN
        mock_increment.assert_called_once_with(
            'task.failed', extra_tags=['name:some.task', 'priority:low', 'exception:ValueError'])
        mock_task_stop.assert_called_once_with(metrics, value=0)

    @mock.patch('helium.common.utils.metricutils.task_stop')
    @mock.patch('helium.common.utils.metricutils.increment')
    def test_task_failure_without_metrics_only_counts_the_failure(self, mock_increment, mock_task_stop):
        # WHEN
        metricutils.task_failure('some.task', exception_type='ValueError')

        # THEN
        mock_increment.assert_called_once()
        mock_task_stop.assert_not_called()
