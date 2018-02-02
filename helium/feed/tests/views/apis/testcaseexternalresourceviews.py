import os

import mock
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.feed.tests.helpers import icalfeedhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseExternalCalendarViews(TestCase):
    def test_externalevent_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_feed_resource_externalcalendaras_externalevents', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user1)

        # WHEN
        responses = [
            self.client.get(
                reverse('api_feed_resource_externalcalendaras_externalevents', kwargs={'pk': external_calendar.pk}))
        ]

        # THEN
        self.assertTrue(ExternalCalendar.objects.filter(pk=external_calendar.pk, user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @mock.patch('helium.feed.services.icalservice.urlopen')
    def test_get_external_calendar_as_external_events(self, mock_urlopen):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user)
        icalfeedhelper.given_urlopen_mock_from_file(os.path.join('resources', 'sample.ical'), mock_urlopen)

        # WHEN
        response = self.client.get(
            reverse('api_feed_resource_externalcalendaras_externalevents', kwargs={'pk': external_calendar.pk}))

        # THEN
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], 'test1')
        self.assertEqual(response.data[0]['all_day'], False)
        self.assertEqual(response.data[0]['show_end_time'], True)
        self.assertEqual(response.data[0]['start'], '2017-08-02T17:34:00Z')
        self.assertEqual(response.data[0]['end'], '2017-08-02T18:04:00Z')
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
