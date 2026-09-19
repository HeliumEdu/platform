from datetime import datetime, timezone
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


class TestCasePresenceMetrics(SimpleTestCase):
    @mock.patch('helium.common.utils.metricutils._current_minute')
    @mock.patch('helium.common.utils.metricutils.is_staff_user', return_value=False)
    @mock.patch('helium.common.utils.metricutils.redisutils.get_redis_client')
    def test_record_presence_adds_user_to_this_minutes_cohort_bucket_with_expiry(
            self, mock_get_client, mock_is_staff, mock_current_minute):
        # GIVEN
        mock_current_minute.return_value = datetime(2026, 9, 19, 14, 7, tzinfo=timezone.utc)
        pipe = mock_get_client.return_value.pipeline.return_value

        # WHEN
        metricutils.record_presence(mock.Mock(pk=42))

        # THEN
        pipe.sadd.assert_called_once_with('presence:users:false:202609191407', 42)
        pipe.expire.assert_called_once_with('presence:users:false:202609191407', 16 * 60)
        pipe.execute.assert_called_once()

    @mock.patch('helium.common.utils.metricutils._current_minute')
    @mock.patch('helium.common.utils.metricutils.is_staff_user', return_value=True)
    @mock.patch('helium.common.utils.metricutils.redisutils.get_redis_client')
    def test_record_presence_keeps_staff_in_their_own_bucket(self, mock_get_client, mock_is_staff, mock_current_minute):
        # GIVEN
        mock_current_minute.return_value = datetime(2026, 9, 19, 14, 7, tzinfo=timezone.utc)
        pipe = mock_get_client.return_value.pipeline.return_value

        # WHEN
        metricutils.record_presence(mock.Mock(pk=7))

        # THEN
        pipe.sadd.assert_called_once_with('presence:users:true:202609191407', 7)

    @mock.patch('helium.common.utils.metricutils.redisutils.get_redis_client', side_effect=RuntimeError('down'))
    def test_record_presence_swallows_redis_failures(self, mock_get_client):
        # WHEN/THEN
        metricutils.record_presence(mock.Mock(pk=42))

    @mock.patch('helium.common.utils.metricutils._current_minute')
    @mock.patch('helium.common.utils.metricutils.redisutils.get_redis_client')
    def test_count_online_users_unions_the_window_of_buckets_ending_now(self, mock_get_client, mock_current_minute):
        # GIVEN
        mock_current_minute.return_value = datetime(2026, 9, 19, 14, 7, tzinfo=timezone.utc)
        mock_get_client.return_value.sunion.return_value = {b'1', b'2', b'3'}

        # WHEN
        count = metricutils.count_online_users('false')

        # THEN
        self.assertEqual(count, 3)
        keys = mock_get_client.return_value.sunion.call_args.args[0]
        self.assertEqual(len(keys), 15)
        self.assertEqual(keys[0], 'presence:users:false:202609191407')
        self.assertEqual(keys[-1], 'presence:users:false:202609191353')

    @mock.patch('helium.common.utils.metricutils.redisutils.get_redis_client', side_effect=RuntimeError('down'))
    def test_count_online_users_is_zero_when_redis_is_unavailable(self, mock_get_client):
        # WHEN/THEN
        self.assertEqual(metricutils.count_online_users('false'), 0)


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
