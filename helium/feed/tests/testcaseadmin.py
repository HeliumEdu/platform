from unittest import mock

from django.conf import settings
from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.admin import ExternalCalendarAdmin, HiddenAfterFailuresFilter, reshow_calendars
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper


class TestCaseAdmin(TestCase):
    def test_reshow_calendars_shows_hidden_calendars_and_resets_failures(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user, shown_on_calendar=False)
        ExternalCalendar.objects.filter(pk=external_calendar.pk).update(
            consecutive_failures=settings.EXTERNAL_CALENDAR_CONSECUTIVE_FAILURE_THRESHOLD, last_sync_error='Timed out',
            etag='"abc"')
        admin_user = userhelper.given_a_user_exists(username='admin', email='admin@test.com')

        # WHEN
        reshow_calendars(mock.Mock(), mock.Mock(user=admin_user),
                         ExternalCalendar.objects.filter(pk=external_calendar.pk))

        # THEN
        external_calendar.refresh_from_db()
        self.assertTrue(external_calendar.shown_on_calendar)
        self.assertEqual(external_calendar.consecutive_failures, 0)
        self.assertIsNone(external_calendar.last_sync_error)
        self.assertIsNone(external_calendar.etag)

    def test_hidden_after_failures_filter_leaves_out_calendars_a_user_hid(self):
        # GIVEN
        user = userhelper.given_a_user_exists()
        hidden_after_failures = externalcalendarhelper.given_external_calendar_exists(user, shown_on_calendar=False)
        ExternalCalendar.objects.filter(pk=hidden_after_failures.pk).update(
            consecutive_failures=settings.EXTERNAL_CALENDAR_CONSECUTIVE_FAILURE_THRESHOLD)
        externalcalendarhelper.given_external_calendar_exists(user, title='Hidden by user', shown_on_calendar=False)
        calendar_filter = HiddenAfterFailuresFilter(None, {'hidden_after_failures': ['yes']}, ExternalCalendar,
                                                    ExternalCalendarAdmin)

        # WHEN
        calendars = calendar_filter.queryset(None, ExternalCalendar.objects.all())

        # THEN
        self.assertEqual(list(calendars), [hidden_after_failures])
