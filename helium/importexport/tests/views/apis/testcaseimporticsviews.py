import datetime
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Course, Event, Homework
from helium.planner.tests.helpers import coursegrouphelper, coursehelper


class TestCaseImportICSViews(APITestCase):
    def _post_ics(self, filename, **fields):
        path = os.path.join(os.path.dirname(__file__), '../../resources', filename)
        with open(path, 'rb') as fp:
            return self.client.post(reverse('importexport_import_ics'), {'file[]': [fp], **fields})

    def test_import_ics_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_import_ics_as_events(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data['courses'])
        self.assertEqual(3, response.data['events'])
        self.assertEqual(0, response.data['homework'])
        events = Event.objects.for_user(user.pk)
        self.assertEqual(3, len(events))
        titles = {event.title for event in events}
        # VTODO, the CANCELLED event, and the duplicate-UID event are all dropped.
        self.assertNotIn('Cancelled Meeting', titles)
        self.assertNotIn('This is a task, not an event', titles)
        self.assertNotIn('Read Chapter 1 (duplicate UID)', titles)
        self.assertEqual({'Read Chapter 1', 'Project Due', 'Lab Session'}, titles)

    def test_import_ics_preserves_all_day_and_description(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        all_day = Event.objects.for_user(user.pk).get(title='Project Due')
        self.assertTrue(all_day.all_day)
        timed = Event.objects.for_user(user.pk).get(title='Read Chapter 1')
        self.assertFalse(timed.all_day)
        self.assertEqual('Pages 1-20', timed.comments)

    def test_import_ics_into_existing_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='course', course=course.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(0, response.data['courses'])
        self.assertEqual(3, response.data['homework'])
        self.assertEqual(0, response.data['events'])
        homework = Homework.objects.for_user(user.pk)
        self.assertEqual(3, len(homework))
        self.assertTrue(all(h.course_id == course.pk for h in homework))

    def test_import_ics_creates_new_course_in_group(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='new_course', course_group=course_group.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data['courses'])
        self.assertEqual(3, response.data['homework'])
        course = Course.objects.for_user(user.pk).get()
        self.assertEqual('My Imported Calendar', course.title)
        self.assertEqual(course_group.pk, course.course_group_id)
        # The new course inherits the group's term, since a calendar carries no start/end.
        self.assertEqual(course_group.start_date, course.start_date)
        self.assertEqual(course_group.end_date, course.end_date)
        self.assertEqual(3, len(Homework.objects.for_user(user.pk)))

    def test_import_ics_empty_calendar_as_events_is_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_empty.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)
        self.assertEqual(0, len(Event.objects.all()))

    def test_import_ics_empty_calendar_leaves_no_new_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self._post_ics('import_empty.ics', target_type='new_course', course_group=course_group.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)
        self.assertEqual(0, len(Course.objects.for_user(user.pk)))
        self.assertEqual(0, len(Homework.objects.for_user(user.pk)))

    def test_import_ics_recurring_expands_into_assignments(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self._post_ics('import_recurring.ics', target_type='course', course=course.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(4, response.data['homework'])
        homework = Homework.objects.for_user(user.pk).order_by('start')
        self.assertEqual(4, len(homework))
        self.assertEqual([datetime.date(2017, 1, 10), datetime.date(2017, 1, 17),
                          datetime.date(2017, 1, 24), datetime.date(2017, 1, 31)],
                         [h.start.date() for h in homework])

    def test_import_ics_recurring_as_events_preserves_rrule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_recurring.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data['events'])
        event = Event.objects.for_user(user.pk).get()
        self.assertIsNotNone(event.recurrence_rule)
        self.assertIn('FREQ=WEEKLY', event.recurrence_rule)

    def test_import_ics_with_abbreviation_timezone(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_abbrev_tz.ics', target_type='events')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data['events'])
        event = Event.objects.for_user(user.pk).get()
        self.assertEqual('Timezone Abbrev Event', event.title)
        # EDT = -0400 per the file's VTIMEZONE, so 09:00 local is 13:00 UTC
        self.assertEqual(datetime.datetime(2026, 7, 1, 13, 0, tzinfo=datetime.timezone.utc), event.start)
        self.assertEqual(datetime.datetime(2026, 7, 1, 14, 0, tzinfo=datetime.timezone.utc), event.end)

    def test_import_ics_rejects_multiple_files(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        file_one = SimpleUploadedFile('a.ics', b'BEGIN:VCALENDAR\nEND:VCALENDAR\n')
        file_two = SimpleUploadedFile('b.ics', b'BEGIN:VCALENDAR\nEND:VCALENDAR\n')
        response = self.client.post(reverse('importexport_import_ics'),
                                    {'file[]': [file_one, file_two], 'target_type': 'events'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_import_ics_requires_target_type(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_generic.ics')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('target_type', response.data)

    def test_import_ics_course_target_requires_course(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='course')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)

    def test_import_ics_rejects_unowned_course(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        other_user = userhelper.given_a_user_exists(username='other_user', email='other@test.com')
        other_course = coursehelper.given_course_exists(
            coursegrouphelper.given_course_group_exists(other_user))

        # WHEN
        response = self._post_ics('import_generic.ics', target_type='course', course=other_course.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)
        self.assertEqual(0, len(Homework.objects.all()))

    def test_import_ics_rejects_invalid_ics(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(
            reverse('importexport_import_ics'),
            {'file[]': [SimpleUploadedFile('not.ics', b'this is not a calendar')], 'target_type': 'events'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)
        self.assertEqual(0, len(Event.objects.all()))
