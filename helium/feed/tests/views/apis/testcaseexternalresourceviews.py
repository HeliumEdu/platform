__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import os
from unittest import mock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.tests.test import CacheTestCase
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.feed.tests.helpers import icalfeedhelper


class TestCaseExternalCalendarResourceViews(APITestCase, CacheTestCase):
    def test_externalevent_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('feed_resource_externalcalendars_events', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user1)

        # WHEN
        responses = [
            self.client.get(
                reverse('feed_resource_externalcalendars_events', kwargs={'pk': external_calendar.pk}))
        ]

        # THEN
        self.assertTrue(ExternalCalendar.objects.filter(pk=external_calendar.pk, user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_get_external_calendar_as_events(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'sample.ical'), mock_urlopen)

        # WHEN
        response = self.client.get(
            reverse('feed_resource_externalcalendars_events', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)
        self.assertEqual(response.data[0]['title'], 'test1')
        self.assertEqual(response.data[0]['all_day'], False)
        self.assertEqual(response.data[0]['show_end_time'], True)
        self.assertEqual(response.data[0]['start'], '2017-08-02T18:34:00Z')
        self.assertEqual(response.data[0]['end'], '2017-08-02T19:04:00Z')
        self.assertEqual(response.data[0]['priority'], 50)
        self.assertEqual(response.data[0]['url'], 'http://www.some-test-url.com')
        self.assertEqual(response.data[0]['comments'], 'test1 description')
        self.assertEqual(response.data[0]['user'], user.pk)
        self.assertEqual(response.data[0]['calendar_item_type'], enums.EXTERNAL)
        self.assertEqual(response.data[1]['title'], 'New Year\'s Day')
        self.assertEqual(response.data[1]['all_day'], True)
        self.assertEqual(response.data[1]['show_end_time'], False)
        self.assertEqual(response.data[1]['start'], '2017-01-01T08:00:00Z')
        self.assertEqual(response.data[1]['end'], '2017-01-02T08:00:00Z')
        self.assertEqual(response.data[1]['priority'], 50)
        self.assertEqual(response.data[1]['url'], None)
        self.assertEqual(response.data[1]['comments'], 'all day event test')
        self.assertEqual(response.data[1]['user'], user.pk)
        self.assertEqual(response.data[1]['calendar_item_type'], enums.EXTERNAL)
        self.assertEqual(response.data[2]['title'], 'EOD Event')
        self.assertEqual(response.data[2]['all_day'], False)
        self.assertEqual(response.data[2]['show_end_time'], True)
        self.assertEqual(response.data[2]['start'], '2020-03-28T15:00:00Z')
        self.assertEqual(response.data[2]['end'], '2020-03-29T07:59:59.999999Z')
        self.assertEqual(response.data[2]['priority'], 50)
        self.assertEqual(response.data[2]['url'], None)
        self.assertEqual(response.data[2]['comments'], 'end date assumed to be EOD')
        self.assertEqual(response.data[2]['user'], user.pk)
        self.assertEqual(response.data[2]['calendar_item_type'], enums.EXTERNAL)
        self.assertEqual(response.data[3]['title'], 'Duration Event')
        self.assertEqual(response.data[3]['all_day'], False)
        self.assertEqual(response.data[3]['show_end_time'], True)
        self.assertEqual(response.data[3]['start'], '2020-03-28T15:00:00Z')
        self.assertEqual(response.data[3]['end'], '2020-03-28T17:00:00Z')
        self.assertEqual(response.data[3]['priority'], 50)
        self.assertEqual(response.data[3]['url'], None)
        self.assertEqual(response.data[3]['comments'], 'end date 2 hours later')
        self.assertEqual(response.data[3]['user'], user.pk)
        self.assertEqual(response.data[3]['calendar_item_type'], enums.EXTERNAL)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_get_external_calendar_cached(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'sample.ical'), mock_urlopen)

        # WHEN
        response_db = self.client.get(
            reverse('feed_resource_externalcalendars_events', kwargs={'pk': external_calendar.pk}))
        with mock.patch('helium.feed.services.icalexternalcalendarservice._create_events_from_calendar') as \
                _create_events_from_calendar:
            response_cached = self.client.get(
                reverse('feed_resource_externalcalendars_events', kwargs={'pk': external_calendar.pk}))

            # THEN
            self.assertEqual(response_db.status_code, status.HTTP_200_OK)
            self.assertEqual(response_cached.status_code, status.HTTP_200_OK)
            self.assertEqual(_create_events_from_calendar.call_count, 0)
            self.assertEqual(len(response_db.data), len(response_cached.data))
            self.assertEqual(response_db.data[0]['title'], response_cached.data[0]['title'])
            self.assertEqual(response_db.data[0]['all_day'], response_cached.data[0]['all_day'])
            self.assertEqual(response_db.data[0]['show_end_time'], response_cached.data[0]['show_end_time'])
            self.assertEqual(response_db.data[0]['start'], response_cached.data[0]['start'])
            self.assertEqual(response_db.data[0]['end'], response_cached.data[0]['end'])
            self.assertEqual(response_db.data[0]['priority'], response_cached.data[0]['priority'])
            self.assertEqual(response_db.data[0]['url'], response_cached.data[0]['url'])
            self.assertEqual(response_db.data[0]['comments'], response_cached.data[0]['comments'])
            self.assertEqual(response_db.data[0]['user'], response_cached.data[0]['user'])
            self.assertEqual(response_db.data[0]['calendar_item_type'], response_cached.data[0]['calendar_item_type'])

    @mock.patch('helium.feed.services.icalexternalcalendarservice.urlopen')
    def test_get_external_calendar_invalid_ical(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'bad.ical'), mock_urlopen)

        # WHEN
        response = self.client.get(
            reverse('feed_resource_externalcalendars_events', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valid ICAL", response.data[0])
        external_calendar = ExternalCalendar.objects.get(pk=external_calendar.pk)
        self.assertFalse(external_calendar.shown_on_calendar)
