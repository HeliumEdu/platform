__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import os
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice
from helium.feed.services.icalexternalcalendarservice import HeliumICalError
from helium.feed.tests.helpers import externalcalendarhelper, icalfeedhelper

logger = logging.getLogger(__name__)


class TestCaseICALExternalCalendarService(TestCase):
    def test_validate_url_file_invalid(self):
        # GIVEN
        with self.assertRaises(HeliumICalError) as ctx:
            icalexternalcalendarservice.validate_url("file://some_local_file.txt")
        self.assertEqual(str(ctx.exception), 'Enter a valid URL.')


class TestCaseFetchIcalConditional(TestCase):
    def setUp(self):
        self.user = userhelper.given_a_user_exists()

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_returns_calendar_on_200(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen,
            etag='"abc123"',
            last_modified='Wed, 01 Jan 2025 00:00:00 GMT'
        )

        # WHEN
        result = icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        self.assertIsNotNone(result)
        # Verify it's a valid calendar object
        self.assertEqual(result.name, 'VCALENDAR')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_stores_etag_header(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        self.assertIsNone(external_calendar.etag)
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen,
            etag='"new-etag-value"'
        )

        # WHEN
        icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        external_calendar.refresh_from_db()
        self.assertEqual(external_calendar.etag, '"new-etag-value"')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_stores_last_modified_header(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        self.assertIsNone(external_calendar.last_modified_header)
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen,
            last_modified='Wed, 01 Jan 2025 12:00:00 GMT'
        )

        # WHEN
        icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        external_calendar.refresh_from_db()
        self.assertEqual(external_calendar.last_modified_header, 'Wed, 01 Jan 2025 12:00:00 GMT')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_sends_if_none_match_header(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.etag = '"existing-etag"'
        external_calendar.save()
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen
        )

        # WHEN
        icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.get_header('If-none-match'), '"existing-etag"')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_sends_if_modified_since_header(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.last_modified_header = 'Wed, 01 Jan 2025 00:00:00 GMT'
        external_calendar.save()
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen
        )

        # WHEN
        icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        self.assertEqual(request.get_header('If-modified-since'), 'Wed, 01 Jan 2025 00:00:00 GMT')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_returns_none_on_304_not_modified(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.etag = '"existing-etag"'
        external_calendar.save()
        icalfeedhelper.given_urlopen_mock_304_not_modified(mock_urlopen)

        # WHEN
        result = icalexternalcalendarservice.fetch_ical_conditional(external_calendar)

        # THEN
        self.assertIsNone(result)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_fetch_raises_on_invalid_ical(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'bad.ical'),
            mock_urlopen
        )

        # WHEN/THEN
        with self.assertRaises(HeliumICalError):
            icalexternalcalendarservice.fetch_ical_conditional(external_calendar)


class TestCaseReindexStaleFeedCaches(TestCase):
    def setUp(self):
        self.user = userhelper.given_a_user_exists()
        cache.clear()

    def tearDown(self):
        cache.clear()

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    @override_settings(FEED_CACHE_REFRESH_TTL_SECONDS=0)
    def test_reindex_fetches_and_parses_stale_feeds(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.last_index = timezone.now() - timezone.timedelta(hours=5)
        external_calendar.save()
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen,
            etag='"new-etag"'
        )

        # WHEN
        icalexternalcalendarservice.reindex_stale_feed_caches()

        # THEN
        external_calendar.refresh_from_db()
        self.assertIsNotNone(external_calendar.last_index)
        self.assertEqual(external_calendar.etag, '"new-etag"')
        mock_urlopen.assert_called_once()

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    @override_settings(FEED_CACHE_REFRESH_TTL_SECONDS=0)
    def test_reindex_handles_304_not_modified(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        old_last_index = timezone.now() - timezone.timedelta(hours=5)
        external_calendar.last_index = old_last_index
        external_calendar.etag = '"existing-etag"'
        external_calendar.save()
        icalfeedhelper.given_urlopen_mock_304_not_modified(mock_urlopen)

        # WHEN
        icalexternalcalendarservice.reindex_stale_feed_caches()

        # THEN
        external_calendar.refresh_from_db()
        # last_index should be updated even on 304
        self.assertGreater(external_calendar.last_index, old_last_index)
        # etag should remain unchanged
        self.assertEqual(external_calendar.etag, '"existing-etag"')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    @override_settings(FEED_CACHE_REFRESH_TTL_SECONDS=0)
    def test_reindex_disables_calendar_on_invalid_url(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.last_index = timezone.now() - timezone.timedelta(hours=5)
        external_calendar.save()
        self.assertTrue(external_calendar.shown_on_calendar)

        magic_mock = mock.MagicMock()
        magic_mock.getcode.return_value = status.HTTP_404_NOT_FOUND
        mock_urlopen.return_value = magic_mock

        # WHEN
        icalexternalcalendarservice.reindex_stale_feed_caches()

        # THEN
        external_calendar.refresh_from_db()
        self.assertFalse(external_calendar.shown_on_calendar)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    @override_settings(FEED_CACHE_REFRESH_TTL_SECONDS=0)
    def test_reindex_clears_cache_on_modified_feed(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.last_index = timezone.now() - timezone.timedelta(hours=5)
        external_calendar.save()

        # Pre-populate cache
        cache_key = f"users:{self.user.pk}:externalcalendars:{external_calendar.pk}:events"
        cache.set(cache_key, '[]', 3600)
        self.assertIsNotNone(cache.get(cache_key))

        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen
        )

        # WHEN
        icalexternalcalendarservice.reindex_stale_feed_caches()

        # THEN - cache should be refreshed with new data
        cached_data = cache.get(cache_key)
        self.assertIsNotNone(cached_data)
        self.assertNotEqual(cached_data, '[]')

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    @override_settings(FEED_CACHE_REFRESH_TTL_SECONDS=0)
    def test_reindex_preserves_cache_on_304(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        external_calendar.last_index = timezone.now() - timezone.timedelta(hours=5)
        external_calendar.etag = '"existing-etag"'
        external_calendar.save()

        # Pre-populate cache with known data
        cache_key = f"users:{self.user.pk}:externalcalendars:{external_calendar.pk}:events"
        cache.set(cache_key, '[{"id": 1, "title": "Cached Event"}]', 3600)

        icalfeedhelper.given_urlopen_mock_304_not_modified(mock_urlopen)

        # WHEN
        icalexternalcalendarservice.reindex_stale_feed_caches()

        # THEN - cache should be preserved (not deleted)
        cached_data = cache.get(cache_key)
        self.assertEqual(cached_data, '[{"id": 1, "title": "Cached Event"}]')


class TestCaseCalendarToEvents(TestCase):
    def setUp(self):
        self.user = userhelper.given_a_user_exists()
        cache.clear()

    def tearDown(self):
        cache.clear()

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_calendar_to_events_returns_events(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)
        icalfeedhelper.given_urlopen_mock_from_file(
            os.path.join('resources', 'sample.ical'),
            mock_urlopen
        )

        # WHEN
        events = icalexternalcalendarservice.calendar_to_events(external_calendar)

        # THEN
        self.assertGreater(len(events), 0)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_calendar_to_events_uses_cache_when_available(self, mock_urlopen):
        # GIVEN
        external_calendar = externalcalendarhelper.given_external_calendar_exists(self.user)

        # Pre-populate cache
        cache_key = f"users:{self.user.pk}:externalcalendars:{external_calendar.pk}:events"
        cached_events = '[{"id": 0, "title": "Cached Event", "all_day": false, "show_end_time": true, ' \
                        '"start": "2025-01-01T10:00:00Z", "end": "2025-01-01T11:00:00Z", ' \
                        '"owner_id": 1, "user": 1, "calendar_item_type": 3, "url": null, "comments": null}]'
        cache.set(cache_key, cached_events, 3600)

        # WHEN
        events = icalexternalcalendarservice.calendar_to_events(external_calendar)

        # THEN
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].title, 'Cached Event')
        # urlopen should not have been called since we used cache
        mock_urlopen.assert_not_called()
