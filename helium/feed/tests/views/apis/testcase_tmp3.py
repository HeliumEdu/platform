import os
from unittest import mock

from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.feed.tests.helpers import externalcalendarhelper
from helium.feed.tests.helpers import icalfeedhelper


def _disabled_calls(mock_increment):
    return [c for c in mock_increment.call_args_list if c.args and c.args[0] == 'feed.ical.disabled']


class TestCaseTmp3(APITestCase, CacheTestCase):
    @mock.patch('helium.feed.services.icalexternalcalendarservice.metricutils.increment')
    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen_secure')
    def test_user_toggling_off_healthy_calendar_emits_nothing(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'sample.ical'), mock_urlopen)

        # WHEN
        response = self.client.patch(
            reverse('feed_externalcalendars_detail', kwargs={'pk': external_calendar.pk}),
            data={'shown_on_calendar': False})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        external_calendar.refresh_from_db()
        self.assertFalse(external_calendar.shown_on_calendar)
        self.assertEqual(_disabled_calls(mock_increment), [])
        print("\n  [user toggle-off, healthy] feed.ical.disabled emitted: 0")

    @mock.patch('helium.feed.services.icalexternalcalendarservice.metricutils.increment')
    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen_secure')
    @override_settings(FEED_CONSECUTIVE_FAILURE_THRESHOLD=2)
    def test_auto_disable_emits_exactly_once(self, mock_urlopen, mock_increment):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'bad.ical'), mock_urlopen)

        # WHEN
        for _ in range(3):
            self.client.get(reverse('feed_externalcalendars_events'))

        # THEN
        external_calendar.refresh_from_db()
        self.assertFalse(external_calendar.shown_on_calendar)
        self.assertEqual(len(_disabled_calls(mock_increment)), 1)
        print("  [auto-disable at threshold] feed.ical.disabled emitted: 1")
