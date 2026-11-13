import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.test import TestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Event
from helium.planner.services import recurrenceservice, reminderservice
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, eventhelper, reminderhelper


class TestCaseRecurrenceService(TestCase):
    def test_bound_to_course_keeps_a_rule_that_already_ends(self):
        # GIVEN
        user = userhelper.given_a_user_exists(time_zone='Europe/Amsterdam')
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        start = datetime.datetime(2017, 4, 3, 16, 0, tzinfo=datetime.timezone.utc)

        for rule in ('FREQ=WEEKLY;BYDAY=MO;COUNT=10', 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20170710T235959Z'):
            with self.subTest(rule=rule):
                # WHEN
                bounded = recurrenceservice.bound_to_course(rule, start, start + datetime.timedelta(hours=1), False,
                                                            course)

                # THEN
                self.assertEqual(bounded, rule)


class TestCaseRecurrenceServiceOccurrenceReminders(TestCase):
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_detaching_an_occurrence_whose_reminder_just_fired_does_not_send_it_again(self, mock_now,
                                                                                      mock_send_notifications):
        for index, (zone, given_series) in enumerate(_zones_and_series()):
            with self.subTest(zone=zone, series=given_series.__name__):
                # GIVEN
                mock_send_notifications.reset_mock()
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(hours=1)
                user = _given_user_with_push_token(index, zone)
                series = given_series(user)
                reminderhelper.given_reminder_exists(user, offset=15, **{_parent_field(series): series})
                mock_now.return_value = occurrence - datetime.timedelta(minutes=14)
                reminderservice.process_push_reminders()
                mock_now.return_value = occurrence - datetime.timedelta(minutes=10)

                # WHEN
                detached = recurrenceservice.detach_occurrence(type(series).objects.get(pk=series.pk), occurrence)
                mock_now.return_value = occurrence - datetime.timedelta(minutes=9)
                reminderservice.process_push_reminders()

                # THEN
                self.assertEqual(mock_send_notifications.call_count, 1)
                clone = detached.reminders.get()
                self.assertTrue(clone.sent)
                self.assertTrue(clone.dismissed)

    @mock.patch('django.utils.timezone.now')
    def test_moving_a_detached_occurrence_forward_rearms_its_already_fired_reminder(self, mock_now):
        for index, (zone, given_series) in enumerate(_zones_and_series()):
            with self.subTest(zone=zone, series=given_series.__name__):
                # GIVEN
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(hours=1)
                user = userhelper.given_a_user_exists(username=f'user{index}', email=f'user{index}@test.com',
                                                      time_zone=zone)
                series = given_series(user)
                reminderhelper.given_reminder_exists(user, offset=15, **{_parent_field(series): series})
                mock_now.return_value = occurrence - datetime.timedelta(minutes=10)
                detached = recurrenceservice.detach_occurrence(series, occurrence)
                moved = occurrence + datetime.timedelta(days=2)

                # WHEN
                detached.start, detached.end = moved, moved + datetime.timedelta(hours=1)
                detached.save()

                # THEN
                reminder = detached.reminders.get()
                self.assertFalse(reminder.sent)
                self.assertFalse(reminder.dismissed)
                self.assertEqual(reminder.start_of_range, moved - datetime.timedelta(minutes=15))

    @mock.patch('helium.planner.handlers.signals.adjust_reminder_times')
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_detaching_the_armed_occurrence_moves_the_series_reminder_on_without_the_adjust_task(
            self, mock_now, mock_send_notifications, mock_adjust_reminder_times):
        for index, (zone, given_series) in enumerate(_zones_and_series()):
            with self.subTest(zone=zone, series=given_series.__name__):
                # GIVEN
                mock_send_notifications.reset_mock()
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(days=1)
                user = _given_user_with_push_token(index, zone)
                series = given_series(user)
                armed = reminderhelper.given_reminder_exists(user, offset=15, **{_parent_field(series): series})

                # WHEN
                recurrenceservice.detach_occurrence(series, occurrence)
                mock_now.return_value = occurrence - datetime.timedelta(minutes=14)
                reminderservice.process_push_reminders()

                # THEN
                armed.refresh_from_db()
                self.assertFalse(armed.sent)
                self.assertEqual(armed.start_of_range,
                                 datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz) - datetime.timedelta(minutes=15))
                self.assertEqual(mock_send_notifications.call_count, 1)

    @mock.patch('helium.planner.handlers.signals.adjust_reminder_times')
    @mock.patch('helium.common.tasks.send_notifications')
    @mock.patch('django.utils.timezone.now')
    def test_deleting_the_armed_occurrence_moves_the_series_reminder_on_without_the_adjust_task(
            self, mock_now, mock_send_notifications, mock_adjust_reminder_times):
        for index, (zone, given_series) in enumerate(_zones_and_series()):
            with self.subTest(zone=zone, series=given_series.__name__):
                # GIVEN
                mock_send_notifications.reset_mock()
                tz = ZoneInfo(zone)
                occurrence = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
                mock_now.return_value = occurrence - datetime.timedelta(days=1)
                user = _given_user_with_push_token(index, zone)
                series = given_series(user)
                armed = reminderhelper.given_reminder_exists(user, offset=15, **{_parent_field(series): series})

                # WHEN
                recurrenceservice.exclude_occurrence(series, occurrence)
                mock_now.return_value = occurrence - datetime.timedelta(minutes=14)
                reminderservice.process_push_reminders()

                # THEN
                armed.refresh_from_db()
                self.assertFalse(armed.sent)
                self.assertEqual(armed.start_of_range,
                                 datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz) - datetime.timedelta(minutes=15))
                mock_send_notifications.assert_not_called()


def _zones_and_series():
    return [(zone, given_series) for zone in ('Europe/Amsterdam', 'America/Los_Angeles')
            for given_series in (_given_weekly_event, _given_weekly_homework)]


def _given_weekly_event(user):
    return eventhelper.given_weekly_event_exists(user)


def _given_weekly_homework(user):
    return coursehelper.given_weekly_homework_in_a_new_course_exists(user)


def _given_user_with_push_token(index, zone):
    user = userhelper.given_a_user_exists(username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
    userhelper.given_user_push_token_exists(user)
    return user


def _parent_field(series):
    return 'event' if isinstance(series, Event) else 'homework'
