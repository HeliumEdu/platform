__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import uuid
from unittest import mock
from zoneinfo import ZoneInfo

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.tests.helpers import (coursegrouphelper, coursehelper, eventhelper,
                                          homeworkhelper, reminderhelper)


def _midnight_in_tz_as_utc(date, tz_name):
    naive = datetime.datetime(date.year, date.month, date.day, 0, 0, 0, 0)
    return naive.replace(tzinfo=ZoneInfo(tz_name)).astimezone(datetime.timezone.utc)


def _put_time_zone(client, time_zone):
    return client.put(
        reverse('auth_user_settings_detail'),
        json.dumps({'time_zone': time_zone}),
        content_type='application/json',
    )


class TestCaseUserSettingsViews(APITestCase):
    def test_user_settings_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('auth_user_settings_detail')),
            self.client.put(reverse('auth_user_settings_detail'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_user_setting(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        self.assertTrue(user.settings.show_getting_started)
        self.assertEqual(user.settings.time_zone, 'America/Los_Angeles')
        self.assertTrue(user.settings.show_planner_tooltips)

        # WHEN
        data = {
            'show_getting_started': False,
            'time_zone': 'America/Chicago',
            'show_planner_tooltips': False,
        }
        response = self.client.put(reverse('auth_user_settings_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['show_getting_started'])
        self.assertEqual(response.data['time_zone'], 'America/Chicago')
        self.assertFalse(response.data['show_planner_tooltips'])
        user.refresh_from_db()
        self.assertFalse(user.settings.show_getting_started)
        self.assertEqual(user.settings.time_zone, response.data['time_zone'])
        self.assertFalse(user.settings.show_planner_tooltips)

    def test_put_bad_data_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'time_zone': 'invalid'
        }
        response = self.client.put(reverse('auth_user_settings_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('time_zone', response.data)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        private_slug = str(uuid.uuid4())
        user.settings.private_slug = private_slug
        user.settings.save()

        # WHEN
        data = {
            'private_slug': 'new_slug'
        }
        response = self.client.put(reverse('auth_user_settings_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertEqual(user.settings.private_slug, private_slug)

    def test_is_setup_complete_in_response(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.get(reverse('auth_user_detail'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_setup_complete', response.data['settings'])

    def test_is_setup_complete_is_read_only(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.is_setup_complete = False
        user.settings.save()

        # WHEN
        data = {
            'is_setup_complete': True
        }
        response = self.client.put(reverse('auth_user_settings_detail'), json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertFalse(user.settings.is_setup_complete)

    def test_timezone_change_rebases_single_day_all_day_event(self):
        # GIVEN
        # All-day event "Project 2" on Friday May 8 2026 in Chicago, stored as midnight CDT
        # (which is 05:00 UTC since CDT = UTC-5 in May).
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            title='Project 2',
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN
        response = _put_time_zone(self.client, 'America/Los_Angeles')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(
            event.start, _midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Los_Angeles')
        )
        self.assertEqual(
            event.end, _midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Los_Angeles')
        )
        # And critically, the local date the user observes in LA is still May 8
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2026, 5, 8))

    def test_timezone_change_rebases_la_to_chicago(self):
        # GIVEN: mirrored bug case (the screenshot showing Project 2 spanning Fri+Sat)
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Los_Angeles'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Los_Angeles'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Los_Angeles'),
        )

        # WHEN
        response = _put_time_zone(self.client, 'America/Chicago')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Chicago')).date(),
                         datetime.date(2026, 5, 8))
        self.assertEqual(event.end.astimezone(ZoneInfo('America/Chicago')).date(),
                         datetime.date(2026, 5, 9))

    def test_timezone_change_rebases_multi_day_all_day_event(self):
        # GIVEN: "Parents Weekend" Oct 31 to Nov 3 in Chicago
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user,
            title='Parents Weekend',
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2025, 10, 31), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2025, 11, 3), 'America/Chicago'),
        )

        # WHEN
        response = _put_time_zone(self.client, 'America/Los_Angeles')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2025, 10, 31))
        self.assertEqual(event.end.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2025, 11, 3))

    def test_timezone_change_leaves_non_all_day_event_alone(self):
        # GIVEN: a 1pm meeting in Chicago should remain at the same UTC instant after tz change
        # (semantically: "same physical moment, displayed in your new local clock")
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        original_start = datetime.datetime(2026, 5, 8, 18, 0, 0, tzinfo=datetime.timezone.utc)
        original_end = datetime.datetime(2026, 5, 8, 19, 0, 0, tzinfo=datetime.timezone.utc)
        event = eventhelper.given_event_exists(
            user, all_day=False, start=original_start, end=original_end,
        )

        # WHEN
        response = _put_time_zone(self.client, 'America/Los_Angeles')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start, original_start)
        self.assertEqual(event.end, original_end)

    def test_timezone_change_rebases_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(
            course,
            all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN
        response = _put_time_zone(self.client, 'America/Los_Angeles')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        homework.refresh_from_db()
        self.assertEqual(homework.start.astimezone(ZoneInfo('America/Los_Angeles')).date(),
                         datetime.date(2026, 5, 8))

    def test_timezone_unchanged_does_not_touch_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        original_start = _midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago')
        event = eventhelper.given_event_exists(
            user, all_day=True,
            start=original_start,
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )

        # WHEN: PUT the same timezone the user already has
        response = _put_time_zone(self.client, 'America/Chicago')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start, original_start)

    @mock.patch('helium.auth.views.apis.usersettingsviews.taskutils.safe_apply_async')
    def test_timezone_change_queues_reminder_recomputation(self, mock_safe_apply_async):
        # GIVEN: an all-day event with a reminder attached
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        event = eventhelper.given_event_exists(
            user, all_day=True,
            start=_midnight_in_tz_as_utc(datetime.date(2026, 5, 8), 'America/Chicago'),
            end=_midnight_in_tz_as_utc(datetime.date(2026, 5, 9), 'America/Chicago'),
        )
        reminderhelper.given_reminder_exists(user, event=event)

        # WHEN
        response = _put_time_zone(self.client, 'America/Los_Angeles')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        queued_calls = [c for c in mock_safe_apply_async.call_args_list
                        if c.kwargs.get('args') == (event.pk, enums.EVENT)]
        self.assertTrue(queued_calls, 'expected adjust_reminder_times to be queued for the event')

    def test_timezone_change_invalidates_course_schedule_cache(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.time_zone = 'America/Chicago'
        user.settings.save()
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # Patch after fixture setup so post_save signals on Course (which themselves clear the
        # cache) don't pollute the call count we're asserting against.
        with mock.patch(
                'helium.auth.views.apis.usersettingsviews.coursescheduleservice.clear_cached_course_schedule'
        ) as mock_clear_course_cache:
            # WHEN
            response = _put_time_zone(self.client, 'America/Los_Angeles')

            # THEN
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            mock_clear_course_cache.assert_called_once_with(course)
