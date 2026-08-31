import datetime
from unittest import mock

from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tasks import reindex_feeds
from helium.feed.tests.helpers import externalcalendarhelper


class TestCaseFeedTasks(TestCase):
    @mock.patch('helium.common.utils.metricutils.increment')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_reports_an_unexpected_error(self, mock_reindex, mock_increment):
        # GIVEN
        mock_reindex.side_effect = ValueError('boom')

        # WHEN
        reindex_feeds.apply(kwargs={'calendar_id': 1}, throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0].kwargs['extra_tags'],
                         ['name:feed.reindex.calendar', 'priority:low', 'exception:ValueError'])

    @mock.patch('helium.common.utils.metricutils.increment')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_reports_a_soft_time_limit(self, mock_reindex, mock_increment):
        # GIVEN
        mock_reindex.side_effect = SoftTimeLimitExceeded()

        # WHEN
        reindex_feeds.apply(kwargs={'calendar_id': 1}, throw=False)

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
        reindex_feeds.apply(kwargs={'calendar_id': 1}, throw=False)

        # THEN
        failed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task.failed']
        self.assertEqual(failed, [])
        completed = [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'task']
        self.assertEqual(completed[0].kwargs['value'], 1)

    @mock.patch('helium.feed.tasks.taskutils.safe_apply_async')
    def test_reindex_feeds_queues_a_task_for_each_stale_calendar(self, mock_apply):
        # GIVEN
        user = userhelper.given_a_user_exists()
        fresh = externalcalendarhelper.given_external_calendar_exists(user, title='fresh')
        ExternalCalendar.objects.filter(pk=fresh.pk).update(last_index=timezone.now())
        stale = externalcalendarhelper.given_external_calendar_exists(user, title='stale')
        ExternalCalendar.objects.filter(pk=stale.pk).update(
            last_index=timezone.now() - datetime.timedelta(
                seconds=settings.FEED_CACHE_REFRESH_TTL_SECONDS + 60))

        # WHEN
        reindex_feeds.apply(throw=False)

        # THEN
        queued = [c.kwargs['kwargs']['calendar_id'] for c in mock_apply.call_args_list]
        self.assertEqual(queued, [stale.pk])

    @mock.patch('helium.feed.tasks.taskutils.safe_apply_async')
    @mock.patch('helium.feed.tasks.icalexternalcalendarservice.reindex_stale_feed_caches')
    def test_reindex_feeds_with_an_id_reindexes_instead_of_dispatching(self, mock_reindex, mock_apply):
        # GIVEN
        calendar_id = 7

        # WHEN
        reindex_feeds.apply(kwargs={'calendar_id': calendar_id}, throw=False)

        # THEN
        mock_reindex.assert_called_once_with(calendar_ids=[calendar_id])
        mock_apply.assert_not_called()
