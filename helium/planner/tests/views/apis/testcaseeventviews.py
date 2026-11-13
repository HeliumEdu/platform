import datetime
import json
from urllib.parse import quote
from zoneinfo import ZoneInfo

from dateutil import parser
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.tests.helpers import commonhelper
from helium.common.utils import datetimeutils
from helium.planner.models import Event, Reminder
from helium.planner.tests.helpers import attachmenthelper, eventhelper, notehelper, occurrencehelper, \
    reminderhelper


class TestCaseEventViews(APITestCase):
    def test_event_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_list')),
            self.client.post(reverse('planner_events_list')),
            self.client.get(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.post(reverse('planner_events_clone', kwargs={'pk': '9999'}))
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def test_get_events(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)

        # WHEN
        response = self.client.get(reverse('planner_events_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Event.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_event(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'priority': 75,
            'owner_id': '12345',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])
        eventhelper.verify_event_matches_data(self, event, data)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_clone_event_copies_fields_and_reminders(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        source = eventhelper.given_event_exists(user, title='Lunch with Pat')
        reminderhelper.given_reminder_exists(user, message='30 min before', offset=30,
                                             offset_type=enums.MINUTES, type=enums.PUSH, event=source)

        # WHEN
        response = self.client.post(reverse('planner_events_clone', kwargs={'pk': source.pk}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Reminder.objects.count(), 2)

        clone = Event.objects.get(pk=response.data['id'])
        self.assertEqual(clone.title, 'Lunch with Pat 1')
        self.assertEqual(clone.start, source.start)
        self.assertEqual(clone.end, source.end)
        self.assertEqual(clone.user_id, user.pk)

        cloned_reminder = clone.reminders.get()
        self.assertEqual(cloned_reminder.offset, 30)
        self.assertFalse(cloned_reminder.sent)
        self.assertFalse(cloned_reminder.dismissed)
        self.assertEqual(cloned_reminder.user_id, user.pk)
        self.assertEqual(cloned_reminder.start_of_range, clone.start - datetime.timedelta(minutes=30))

    def test_clone_recurring_event_returns_non_recurring_event_at_requested_occurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        source = eventhelper.given_event_exists(user, recurrence_rule='FREQ=WEEKLY;BYDAY=MO',
                                                start=datetime.datetime(2017, 5, 8, 12, 0, 0,
                                                                        tzinfo=datetime.timezone.utc),
                                                end=datetime.datetime(2017, 5, 8, 14, 0, 0,
                                                                      tzinfo=datetime.timezone.utc))
        occurrence_start = datetime.datetime(2017, 5, 22, 12, 0, 0, tzinfo=datetime.timezone.utc)

        # WHEN
        response = _clone(self.client, source, occurrence_start)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        clone = Event.objects.get(pk=response.data['id'])
        self.assertIsNone(clone.recurrence_rule)
        self.assertEqual(clone.start, occurrence_start)
        self.assertEqual(clone.end, occurrence_start + datetime.timedelta(hours=2))

    def test_clone_recurring_event_at_non_occurrence_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        source = eventhelper.given_event_exists(user, recurrence_rule='FREQ=WEEKLY;BYDAY=MO')

        # WHEN
        response = self.client.post(reverse('planner_events_clone', kwargs={'pk': source.pk}) +
                                    '?occurrence_start=2017-05-23T12:00:00Z')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('occurrence_start', response.data)
        self.assertEqual(Event.objects.count(), 1)

    def test_clone_endless_event_past_the_horizon_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        source = eventhelper.given_event_exists(user, recurrence_rule='FREQ=DAILY')

        # WHEN
        response = _clone(self.client, source, source.start.replace(year=9999))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('occurrence_start', response.data)
        self.assertEqual(Event.objects.count(), 1)

    def test_clone_event_other_user_returns_404(self):
        # GIVEN
        owner = userhelper.given_a_user_exists()
        owner_source = eventhelper.given_event_exists(owner)
        reminderhelper.given_reminder_exists(owner, event=owner_source)

        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                            email='test2@email.com')

        # WHEN
        response = self.client.post(reverse('planner_events_clone', kwargs={'pk': owner_source.pk}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    def test_create_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00-0500',
            'end': '2014-05-08T14:00:00-0500',
            'priority': 75,
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'user': user.pk
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.get(pk=response.data['id'])
        self.assertEqual(event.start.isoformat(), parser.parse(data['start']).astimezone(datetime.timezone.utc).isoformat())
        self.assertEqual(event.end.isoformat(), parser.parse(data['end']).astimezone(datetime.timezone.utc).isoformat())

    def test_create_rejects_naive_datetime(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08 12:00:00',
            'end': '2014-05-08 14:00:00',
            'priority': 75,
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Event.objects.count(), 0)
        self.assertIn('start', response.data)
        self.assertIn('timezone', str(response.data['start']))

    def test_get_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.get(reverse('planner_events_detail',
                                           kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_update_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        self.assertEqual(event.title, '🏀 Test Event')

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-08T14:00:00Z',
            'priority': 12,
            'owner_id': '54321'
        }
        response = self.client.put(reverse('planner_events_detail',
                                           kwargs={'pk': event.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        event.refresh_from_db()
        eventhelper.verify_event_matches_data(self, event, response.data)

    def test_update_start_before_end_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-07T14:00:00Z',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('must be before', response.data['non_field_errors'][0])

    def test_patch_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00-0500',
            'end': '2016-05-08T14:00:00-0500',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.start.isoformat(), parser.parse(data['start']).astimezone(datetime.timezone.utc).isoformat())
        self.assertEqual(event.end.isoformat(), parser.parse(data['end']).astimezone(datetime.timezone.utc).isoformat())

    def test_patch_rejects_naive_datetime(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/New_York')
        event = eventhelper.given_event_exists(user)
        original_start = event.start

        # WHEN
        data = {
            'start': '2016-05-08 12:00:00',
            'end': '2016-05-08 14:00:00',
        }
        response = self.client.patch(reverse('planner_events_detail',
                                             kwargs={'pk': event.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)
        event.refresh_from_db()
        self.assertEqual(event.start, original_start)

    def test_delete_event_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        response = self.client.delete(reverse('planner_events_detail',
                                              kwargs={'pk': event.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=event.pk).exists())
        self.assertEqual(Event.objects.count(), 0)

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_detail', kwargs={'pk': event.pk})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': event.pk})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': event.pk}))
        ]

        # THEN
        self.assertTrue(Event.objects.filter(pk=event.pk, user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_recurring_event_persists_rrule_and_exdates(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Weekly study group',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=WEEKLY;BYDAY=MO',
            'exception_dates': ['2025-10-13T18:00:00Z'],
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO')
        self.assertEqual(response.data['exception_dates'], ['2025-10-13T18:00:00Z'])
        event = Event.objects.get(pk=response.data['id'])
        self.assertEqual(event.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO')
        self.assertEqual(event.exception_dates, ['2025-10-13T18:00:00Z'])
        self.assertEqual(event.user_id, user.pk)

        # AND the GET round-trips both fields
        get_response = self.client.get(
            reverse('planner_events_detail', kwargs={'pk': event.pk}))
        self.assertEqual(get_response.data['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO')
        self.assertEqual(get_response.data['exception_dates'], ['2025-10-13T18:00:00Z'])

    def test_create_event_with_utc_until_recurrence_rule(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Weekly quiz',
            'all_day': False,
            'show_end_time': True,
            'start': '2026-10-14T16:00:00Z',
            'end': '2026-10-14T17:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=WEEKLY;UNTIL=20261126T000000Z;BYDAY=WE',
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recurrence_rule'], 'FREQ=WEEKLY;UNTIL=20261126T000000Z;BYDAY=WE')

    def test_get_events_in_later_window_includes_recurring_series_anchored_before_it(self):
        for zone_name in ('Europe/Amsterdam', 'America/Los_Angeles'):
            with self.subTest(zone=zone_name):
                # GIVEN
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user_{zone_name}', email=f'{zone_name}@test.com', time_zone=zone_name)
                series_start = datetime.datetime(2026, 10, 6, 10, 0, tzinfo=ZoneInfo(zone_name))
                series = eventhelper.given_event_exists(user, title='Series', start=series_start,
                                                        end=series_start + datetime.timedelta(hours=1),
                                                        recurrence_rule='FREQ=WEEKLY;COUNT=5;BYDAY=TU')
                eventhelper.given_event_exists(user, title='One-off', start=series_start,
                                               end=series_start + datetime.timedelta(hours=1))

                # WHEN
                response = self.client.get(reverse('planner_events_list') + '?from=2026-11-01&to=2026-12-13')

                # THEN
                self.assertEqual([event['id'] for event in response.data], [series.pk],
                                 'the series overlaps November; the October one-off does not')

    def test_create_event_without_recurrence_defaults_to_null(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'One-off meeting',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data['recurrence_rule'])
        self.assertIsNone(response.data['exception_dates'])

    def test_blank_recurrence_rule_is_stored_as_null(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        data = {
            'title': 'One-off meeting',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
            'recurrence_rule': '',
        }

        # WHEN
        created = self.client.post(reverse('planner_events_list'), json.dumps(data), content_type='application/json')
        patched = self.client.patch(reverse('planner_events_detail', kwargs={'pk': event.pk}),
                                    json.dumps({'recurrence_rule': ''}), content_type='application/json')

        # THEN
        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(patched.status_code, status.HTTP_200_OK)
        self.assertIsNone(created.data['recurrence_rule'])
        self.assertIsNone(patched.data['recurrence_rule'])
        self.assertEqual(Event.objects.filter(recurrence_rule__isnull=True).count(), 2)

    def test_create_event_rejects_malformed_recurrence_rule(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Bad RRULE',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=NOPE;BANANA',
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recurrence_rule', response.data)

    def test_create_event_weekly_rrule_without_byday_inferred(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Weekly study group',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=WEEKLY',
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO')
        event = Event.objects.get(pk=response.data['id'])
        self.assertEqual(event.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO')

    def test_create_event_rejects_unsupported_rrule_properties(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        base = {'title': 'Bad', 'all_day': False, 'show_end_time': True,
                'start': '2025-09-01T18:00:00Z', 'end': '2025-09-01T19:00:00Z', 'priority': 50}

        # WHEN / THEN
        for rule in ('FREQ=HOURLY;COUNT=5', 'FREQ=WEEKLY;BYDAY=MO;WKST=SU'):
            response = self.client.post(reverse('planner_events_list'),
                                        json.dumps({**base, 'recurrence_rule': rule}),
                                        content_type='application/json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, msg=rule)
            self.assertIn('recurrence_rule', response.data)

    def test_create_event_monthly_ordinal_byday_normalized_to_bysetpos(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Club meeting',
            'all_day': False,
            'show_end_time': True,
            'start': '2026-10-13T16:00:00Z',
            'end': '2026-10-13T17:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=MONTHLY;BYDAY=2TU',
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['recurrence_rule'], 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2')
        event = Event.objects.get(pk=response.data['id'])
        self.assertEqual(event.recurrence_rule, 'FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2')

    def test_create_event_yearly_rule_infers_month_and_day_in_user_zone(self):
        for zone_name, expected in (('Europe/Amsterdam', 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=14'),
                                    ('America/Los_Angeles', 'FREQ=YEARLY;BYMONTH=10;BYMONTHDAY=13')):
            with self.subTest(zone=zone_name):
                # GIVEN
                userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user_{zone_name}', email=f'{zone_name}@test.com', time_zone=zone_name)

                # WHEN
                data = {
                    'title': 'Anniversary',
                    'all_day': False,
                    'show_end_time': True,
                    'start': '2026-10-13T23:30:00Z',
                    'end': '2026-10-14T00:30:00Z',
                    'priority': 50,
                    'recurrence_rule': 'FREQ=YEARLY',
                }
                response = self.client.post(reverse('planner_events_list'),
                                            json.dumps(data), content_type='application/json')

                # THEN
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data['recurrence_rule'], expected,
                                 'the day is the start\'s local date in the user\'s zone, where the client expands it')

    def test_create_event_weekly_rrule_without_byday_inferred_in_user_zone(self):
        for zone_name, expected in (('Europe/Amsterdam', 'FREQ=WEEKLY;BYDAY=WE'),
                                    ('America/Los_Angeles', 'FREQ=WEEKLY;BYDAY=TU')):
            with self.subTest(zone=zone_name):
                # GIVEN
                userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user_{zone_name}', email=f'{zone_name}@test.com', time_zone=zone_name)

                # WHEN
                data = {
                    'title': 'Late study group',
                    'all_day': False,
                    'show_end_time': True,
                    'start': '2026-10-13T23:30:00Z',
                    'end': '2026-10-14T00:30:00Z',
                    'priority': 50,
                    'recurrence_rule': 'FREQ=WEEKLY',
                }
                response = self.client.post(reverse('planner_events_list'),
                                            json.dumps(data), content_type='application/json')

                # THEN
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.data['recurrence_rule'], expected,
                                 'the weekday is the start\'s local weekday in the user\'s zone, not its UTC weekday')

    def test_patch_event_rule_normalized_against_stored_start(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        start = datetime.datetime(2026, 10, 13, 23, 30, tzinfo=datetime.timezone.utc)
        event = eventhelper.given_event_exists(user, start=start, end=start + datetime.timedelta(hours=1))

        # WHEN
        response = self.client.patch(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps({'recurrence_rule': 'FREQ=MONTHLY'}),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.recurrence_rule, 'FREQ=MONTHLY;BYMONTHDAY=14')

    def test_patch_event_without_rule_leaves_stored_rule_unchanged(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user, recurrence_rule='FREQ=MONTHLY;BYMONTHDAY=8')

        # WHEN
        response = self.client.patch(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps({'title': 'Renamed'}),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertEqual(event.recurrence_rule, 'FREQ=MONTHLY;BYMONTHDAY=8')

    def test_create_event_rejects_monthly_and_yearly_rules_sfcalendar_cannot_expand(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        base = {'title': 'Bad', 'all_day': False, 'show_end_time': True,
                'start': '2026-10-13T16:00:00Z', 'end': '2026-10-13T17:00:00Z', 'priority': 50}

        for rule in ('FREQ=MONTHLY;BYDAY=TU', 'FREQ=MONTHLY;BYDAY=MO,WE', 'FREQ=MONTHLY;BYDAY=5FR',
                     'FREQ=YEARLY;BYMONTHDAY=15', 'FREQ=YEARLY;BYMONTH=11;BYDAY=TH'):
            with self.subTest(rule=rule):
                # WHEN
                response = self.client.post(reverse('planner_events_list'),
                                            json.dumps({**base, 'recurrence_rule': rule}),
                                            content_type='application/json')

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('recurrence_rule', response.data)

    def test_create_event_rejects_non_list_exception_dates(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'Bad exdates',
            'all_day': False,
            'show_end_time': True,
            'start': '2025-09-01T18:00:00Z',
            'end': '2025-09-01T19:00:00Z',
            'priority': 50,
            'recurrence_rule': 'FREQ=DAILY',
            'exception_dates': 'not-a-list',
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('exception_dates', response.data)

    def test_patch_event_clears_recurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        event.recurrence_rule = 'FREQ=WEEKLY;BYDAY=MO'
        event.exception_dates = ['2025-10-13T18:00:00Z']
        event.save(update_fields=['recurrence_rule', 'exception_dates'])

        # WHEN
        response = self.client.patch(
            reverse('planner_events_detail', kwargs={'pk': event.pk}),
            json.dumps({'recurrence_rule': None, 'exception_dates': None}),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event.refresh_from_db()
        self.assertIsNone(event.recurrence_rule)
        self.assertIsNone(event.exception_dates)

    def test_create_bad_data(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.post(reverse('planner_events_list'),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.put(reverse('planner_events_detail', kwargs={'pk': event.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_not_found(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        responses = [
            self.client.get(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_events_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_events_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        commonhelper.verify_responses_hide_other_users_data(self, responses)

    def test_range_query(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2017, 5, 8, 16, 0, 0, tzinfo=datetime.timezone.utc),
                                       end=datetime.datetime(2017, 5, 8, 16, 59, 0, tzinfo=datetime.timezone.utc))
        event2 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2017, 5, 8, 17, 0, 0, tzinfo=datetime.timezone.utc),
                                                end=datetime.datetime(2017, 5, 8, 18, 0, 0, tzinfo=datetime.timezone.utc))
        event4 = eventhelper.given_event_exists(user,
                                                start=datetime.datetime(2017, 5, 8, 19, 30, 0, tzinfo=datetime.timezone.utc),
                                                end=datetime.datetime(2017, 5, 8, 20, 0, 0, tzinfo=datetime.timezone.utc))
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2017, 5, 8, 20, 1, 0, tzinfo=datetime.timezone.utc),
                                       end=datetime.datetime(2017, 5, 8, 21, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(
            reverse(
                'planner_events_list') + f'?from={quote(event2.start.isoformat())}&to={quote(event4.end.isoformat())}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_range_query_multiday(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(user,
                                       start=datetime.datetime(2025, 10, 31, 0, 0, 0, tzinfo=datetime.timezone.utc),
                                       end=datetime.datetime(2025, 11, 2, 0, 0, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(
            reverse(
                'planner_events_list') + f'?from=2025-11-01T00:00:00Z&to=2025-11-02T00:00:00Z')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_title_search_query(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user, title='test1')
        eventhelper.given_event_exists(user, title='test2')

        # WHEN
        response = self.client.get(reverse('planner_events_list') + '?search=tEst1')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], event.title)

    def test_events_for_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)
        eventhelper.given_event_exists(user2)
        self.assertEqual(Event.objects.count(), 4)

        # WHEN
        response = self.client.delete(reverse('planner_events_resource_delete'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Event.objects.count(), 1)
        self.assertEqual(Event.objects.for_user(user2.pk).count(), 0)

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event1 = eventhelper.given_event_exists(user)
        event2 = eventhelper.given_event_exists(user)
        event3 = eventhelper.given_event_exists(user)

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Event.objects.filter(pk=event1.pk).update(updated_at=old_time)
        Event.objects.filter(pk=event2.pk).update(updated_at=recent_time)
        Event.objects.filter(pk=event3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_events_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(event2.pk, returned_ids)
        self.assertIn(event3.pk, returned_ids)
        self.assertNotIn(event1.pk, returned_ids)

    def test_filter_id_cannot_access_other_users_data(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        event = eventhelper.given_event_exists(user1)

        # WHEN
        response = self.client.get(reverse('planner_events_list') + f'?id={event.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestCaseEventOccurrenceViews(APITestCase):
    def test_patch_this_occurrence_detaches_it_with_its_own_times_and_reminders(self):
        for index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
                series = _given_weekly_series(user, tz)
                reminderhelper.given_reminder_exists(user, event=series, offset=30)
                attachment = attachmenthelper.given_attachment_exists(user, event=series)
                note = notehelper.given_note_linked_to_event(user, series)
                occurrence = datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz)
                moved = datetime.datetime(2030, 5, 21, 14, 0, tzinfo=tz)

                # WHEN
                response = _patch(
                    self.client, series, {'title': 'Lecture (Room 2)', 'start': moved.isoformat(),
                                          'end': (moved + datetime.timedelta(hours=2)).isoformat()},
                    occurrencehelper.occurrence_query(occurrence))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                detached = Event.objects.get(pk=response.data['id'])
                self.assertNotEqual(detached.pk, series.pk)
                self.assertEqual(detached.title, 'Lecture (Room 2)')
                self.assertEqual(detached.start, moved)
                self.assertEqual(detached.end, moved + datetime.timedelta(hours=2))
                self.assertIsNone(detached.recurrence_rule)
                reminder = detached.reminders.get()
                self.assertFalse(reminder.sent)
                self.assertEqual(reminder.offset, 30)
                self.assertEqual(reminder.start_of_range, moved - datetime.timedelta(minutes=30))
                self.assertEqual(detached.attachments.count(), 0)
                self.assertEqual(detached.notes_set.count(), 0)
                series.refresh_from_db()
                self.assertEqual(series.exception_dates, [datetimeutils.as_utc_iso(occurrence)])
                self.assertEqual(series.title, 'Lecture')
                self.assertEqual(list(series.attachments.all()), [attachment])
                self.assertEqual(list(note.events.all()), [series])

    def test_patch_this_occurrence_rejects_what_is_not_a_remaining_occurrence(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz)
        excluded = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
        series.exception_dates = [datetimeutils.as_utc_iso(excluded)]
        series.save()
        single = eventhelper.given_event_exists(user, start=datetime.datetime(2030, 5, 6, 7, 0, tzinfo=datetime.timezone.utc))
        cases = (
            (series, occurrencehelper.occurrence_query(datetime.datetime(2030, 5, 7, 9, 0, tzinfo=tz)),
             'occurrence_start'),
            (series, occurrencehelper.occurrence_query(excluded), 'occurrence_start'),
            (series, 'scope=this', 'occurrence_start'),
            (series, 'scope=some&occurrence_start=2030-05-20T07:00:00Z', 'scope'),
            (series, 'scope=this&occurrence_start=2030-05-20T09:00:00', 'occurrence_start'),
            (single, 'scope=this&occurrence_start=2030-05-06T07:00:00Z', 'non_field_errors'),
        )

        for event, query, error_key in cases:
            with self.subTest(query=query):
                # WHEN
                response = _patch(self.client, event, {'title': 'Moved'}, query)

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                if error_key != 'non_field_errors':
                    self.assertIn(error_key, response.data)
                self.assertEqual(Event.objects.count(), 2)
                series.refresh_from_db()
                self.assertEqual(series.exception_dates, [datetimeutils.as_utc_iso(excluded)])
                self.assertEqual(series.title, 'Lecture')

    def test_patch_this_last_remaining_occurrence_hands_note_and_attachments_over(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz, rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2')
        series.exception_dates = [datetimeutils.as_utc_iso(series.start)]
        series.save()
        reminderhelper.given_reminder_exists(user, event=series)
        attachment = attachmenthelper.given_attachment_exists(user, event=series)
        note = notehelper.given_note_linked_to_event(user, series)
        last = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)

        # WHEN
        response = _patch(self.client, series, {'title': 'Final lecture'}, occurrencehelper.occurrence_query(last))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Event.objects.filter(pk=series.pk).exists())
        detached = Event.objects.get(pk=response.data['id'])
        self.assertEqual(detached.title, 'Final lecture')
        self.assertEqual(detached.start, last)
        self.assertEqual(list(note.events.all()), [detached])
        attachment.refresh_from_db()
        self.assertEqual(attachment.event_id, detached.pk)
        self.assertEqual(detached.reminders.count(), 1)

    def test_patch_from_an_occurrence_moves_the_whole_series(self):
        for index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
                series = _given_weekly_series(user, tz)
                series.exception_dates = [datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 27, 9, 0, tzinfo=tz))]
                series.save()
                occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
                moved = datetime.datetime(2030, 5, 14, 10, 30, tzinfo=tz)

                # WHEN
                response = _patch(self.client, series, {'start': moved.isoformat(),
                                                        'end': (moved + datetime.timedelta(hours=2)).isoformat()},
                                  occurrencehelper.occurrence_query(occurrence, scope=None))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data['id'], series.pk)
                series.refresh_from_db()
                self.assertEqual(series.start, datetime.datetime(2030, 5, 7, 10, 30, tzinfo=tz))
                self.assertEqual(series.end - series.start, datetime.timedelta(hours=2))
                self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=TU')
                self.assertEqual(series.exception_dates,
                                 [datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 28, 10, 30, tzinfo=tz))])
                self.assertEqual(Event.objects.filter(user=user).count(), 1)

    def test_patch_series_start_without_a_rule_moves_rule_and_exceptions(self):
        # GIVEN
        tz = ZoneInfo('America/Los_Angeles')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/Los_Angeles')
        series = _given_weekly_series(user, tz, rule='FREQ=WEEKLY;BYDAY=MO;UNTIL=20300701T065959Z')
        series.exception_dates = [datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz))]
        series.save()
        new_start = datetime.datetime(2030, 5, 8, 9, 0, tzinfo=tz)

        # WHEN
        response = self.client.patch(reverse('planner_events_detail', kwargs={'pk': series.pk}),
                                     json.dumps({'start': new_start.isoformat(),
                                                 'end': (new_start + datetime.timedelta(hours=1)).isoformat()}),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        series.refresh_from_db()
        self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=WE;UNTIL=20300703T065959Z')
        self.assertEqual(series.exception_dates,
                         [datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 22, 9, 0, tzinfo=tz))])

    def test_patch_series_start_with_an_explicit_rule_keeps_that_rule(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz)
        new_start = datetime.datetime(2030, 5, 10, 9, 0, tzinfo=tz)

        # WHEN
        response = self.client.patch(reverse('planner_events_detail', kwargs={'pk': series.pk}),
                                     json.dumps({'start': new_start.isoformat(),
                                                 'end': (new_start + datetime.timedelta(hours=1)).isoformat(),
                                                 'recurrence_rule': 'FREQ=WEEKLY;BYDAY=FR,MO'}),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        series.refresh_from_db()
        self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=FR,MO')

    def test_patch_from_an_occurrence_with_only_end_keeps_the_series_start(self):
        for index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
                series = _given_weekly_series(user, tz)
                occurrence = datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz)

                # WHEN
                response = _patch(self.client, series, {'end': (occurrence + datetime.timedelta(hours=2)).isoformat()},
                                  occurrencehelper.occurrence_query(occurrence, scope=None))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                series.refresh_from_db()
                self.assertEqual(series.start, datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz))
                self.assertEqual(series.end - series.start, datetime.timedelta(hours=2))

    def test_patch_from_an_occurrence_with_only_start_keeps_the_occurrence_duration(self):
        for zone_index, zone in enumerate(('Europe/Amsterdam', 'America/Los_Angeles')):
            tz = ZoneInfo(zone)
            cases = (
                (datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz), datetime.datetime(2030, 5, 6, 9, 30, tzinfo=tz),
                 datetime.datetime(2030, 5, 6, 9, 30, tzinfo=tz)),
                (datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz), datetime.datetime(2030, 5, 21, 10, 0, tzinfo=tz),
                 datetime.datetime(2030, 5, 7, 10, 0, tzinfo=tz)),
            )
            for case_index, (occurrence, moved, expected_start) in enumerate(cases):
                with self.subTest(zone=zone, occurrence=occurrence):
                    # GIVEN
                    username = f'user{zone_index}{case_index}'
                    user = userhelper.given_a_user_exists_and_is_authenticated(
                        self.client, username=username, email=f'{username}@test.com', time_zone=zone)
                    series = _given_weekly_series(user, tz)

                    # WHEN
                    response = _patch(self.client, series, {'start': moved.isoformat()},
                                      occurrencehelper.occurrence_query(occurrence, scope=None))

                    # THEN
                    self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                    series.refresh_from_db()
                    self.assertEqual(series.start, expected_start)
                    self.assertEqual(series.end - series.start, datetime.timedelta(hours=1))

    def test_delete_this_occurrence_leaves_it_out_of_the_series(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz)
        occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)

        # WHEN
        response = _delete(self.client, series, occurrencehelper.occurrence_query(occurrence))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        series.refresh_from_db()
        self.assertEqual(series.exception_dates, [datetimeutils.as_utc_iso(occurrence)])
        self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO')

    def test_delete_this_last_remaining_occurrence_deletes_the_series(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz, rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2')
        series.exception_dates = [datetimeutils.as_utc_iso(series.start)]
        series.save()
        note = notehelper.given_note_linked_to_event(user, series)

        # WHEN
        response = _delete(self.client, series, occurrencehelper.occurrence_query('2030-05-13T07:00:00Z'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Event.objects.filter(pk=series.pk).exists())
        self.assertFalse(type(note).objects.filter(pk=note.pk).exists())

    def test_patch_clearing_the_rule_drops_fired_reminder_records(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        series = _given_weekly_series(user, tz)
        active = reminderhelper.given_reminder_exists(user, event=series, offset=15)
        fired = reminderhelper.given_reminder_exists(user, event=series, offset=15)
        Reminder.objects.filter(pk=fired.pk).update(sent=True)
        other_offset_fired = reminderhelper.given_reminder_exists(user, event=series, offset=60)
        Reminder.objects.filter(pk=other_offset_fired.pk).update(sent=True)

        # WHEN
        response = self.client.patch(reverse('planner_events_detail', kwargs={'pk': series.pk}),
                                     json.dumps({'recurrence_rule': None}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(series.reminders.values_list('pk', flat=True)), {active.pk, other_offset_fired.pk})


def _given_weekly_series(user, tz, rule='FREQ=WEEKLY;BYDAY=MO'):
    return eventhelper.given_weekly_event_exists(user, title='Lecture',
                                                 start=datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz),
                                                 recurrence_rule=rule)


def _patch(client, event, data, query):
    return client.patch(f"{reverse('planner_events_detail', kwargs={'pk': event.pk})}?{query}",
                        json.dumps(data), content_type='application/json')


def _delete(client, event, query):
    return client.delete(f"{reverse('planner_events_detail', kwargs={'pk': event.pk})}?{query}")


def _clone(client, event, occurrence_start):
    return client.post(f"{reverse('planner_events_clone', kwargs={'pk': event.pk})}?"
                       f"{occurrencehelper.occurrence_query(occurrence_start, scope=None)}")
