from unittest import mock

from celery.exceptions import SoftTimeLimitExceeded
from django.test import TestCase

from helium.feed.tasks import reindex_feeds


class TestCaseFeedTasks(TestCase):
    @mock.patch('helium.common.utils.metricutils.increment')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_reports_an_unexpected_error(self, mock_reindex, mock_increment):
        # GIVEN
        mock_reindex.side_effect = ValueError('boom')

        # WHEN
        reindex_feeds.apply(throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].kwargs['extra_tags'],
                         ['name:feed.reindex', 'priority:low', 'exception:ValueError'])

    @mock.patch('helium.common.utils.metricutils.increment')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_reports_a_soft_time_limit(self, mock_reindex, mock_increment):
        # GIVEN
        mock_reindex.side_effect = SoftTimeLimitExceeded()

        # WHEN
        reindex_feeds.apply(throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(len(failed), 1)
        self.assertIn('exception:SoftTimeLimitExceeded', failed[0].kwargs['extra_tags'])

    @mock.patch('helium.common.utils.metricutils.increment')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_reports_success(self, mock_reindex, mock_increment):
        # GIVEN
        mock_reindex.return_value = None

        # WHEN
        reindex_feeds.apply(throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(failed, [])
        completed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task']
        self.assertEqual(completed[0].kwargs['value'], 1)
