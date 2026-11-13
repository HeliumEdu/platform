import datetime
import os

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Category, Course, Event, Homework, Note
from helium.planner.tests.helpers import coursegrouphelper, coursehelper


class TestCaseImportICSViews(APITestCase):
    def _post_ics(self, filename, **fields):
        path = os.path.join(os.path.dirname(__file__), '../../resources', filename)
        with open(path, 'rb') as fp:
            return self.client.post(reverse('importexport_import_ics'), {'file[]': [fp], **fields})

    def _post_inline_ics(self, events, course):
        calendar = ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n' + events + 'END:VCALENDAR\r\n').encode()
        return self.client.post(reverse('importexport_import_ics'),
                                {'file[]': [SimpleUploadedFile('calendar.ics', calendar)], 'target_type': 'course',
                                 'course': course.pk})

    def _given_course(self, end_date=datetime.date(2017, 5, 8)):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, end_date=end_date)
        return coursehelper.given_course_exists(course_group, end_date=end_date)

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

    def test_import_ics_preserves_all_day_and_keeps_description_as_a_linked_note(self):
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
        self.assertEqual({'ops': [{'insert': 'Pages 1-20\n'}]}, timed.notes_set.get().content)
        self.assertFalse(all_day.notes_set.exists())
        self.assertEqual(1, Note.objects.for_user(user.pk).count())

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
        described = homework.get(title='Read Chapter 1')
        self.assertEqual({'ops': [{'insert': 'Pages 1-20\n'}]}, described.notes_set.get().content)
        self.assertEqual(1, Note.objects.for_user(user.pk).count())

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

    def test_import_ics_recurring_creates_a_repeating_assignment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self._post_ics('import_recurring.ics', target_type='course', course=course.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data['homework'])
        homework = Homework.objects.get(course=course)
        self.assertEqual((homework.title, homework.recurrence_rule), ('Weekly Quiz', 'FREQ=WEEKLY;COUNT=4;BYDAY=TU'))
        self.assertEqual([datetime.date(2017, 1, 10), datetime.date(2017, 1, 17),
                          datetime.date(2017, 1, 24), datetime.date(2017, 1, 31)],
                         [start.date() for start, _ in homework.occurrences()])

    def test_import_ics_recurring_assignments_land_in_uncategorized(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self._post_ics('import_recurring.ics', target_type='course', course=course.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(1, response.data['homework'])
        uncategorized = Category.objects.get(course=course, title='Uncategorized')
        homework = Homework.objects.for_user(user.pk)
        self.assertTrue(all(h.category_id == uncategorized.pk for h in homework))
        self.assertTrue(all(h.completed_at is None for h in homework))
        self.assertTrue(all(h.current_grade == '-1/100' for h in homework))

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

    def test_import_ics_dry_run_saves_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        path = os.path.join(os.path.dirname(__file__), '../../resources', 'import_generic.ics')

        # WHEN
        with open(path, 'rb') as fp:
            response = self.client.post(f"{reverse('importexport_import_ics')}?dry_run=true",
                                        {'file[]': [fp], 'target_type': 'course', 'course': course.pk})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(3, response.data['homework'])
        self.assertFalse(Homework.objects.filter(course=course).exists())

    def test_import_ics_dry_run_reports_the_same_errors(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        path = os.path.join(os.path.dirname(__file__), '../../resources', 'import_generic.ics')

        # WHEN
        with open(path, 'rb') as fp:
            response = self.client.post(f"{reverse('importexport_import_ics')}?dry_run=true",
                                        {'file[]': [fp], 'target_type': 'course', 'course': 9999})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course', response.data)

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

    def test_import_ics_recurring_exdates_become_skipped_occurrences(self):
        # GIVEN
        course = self._given_course()

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:quiz\r\nSUMMARY:Quiz\r\nDTSTART:20170110T140000Z\r\nDTEND:20170110T150000Z\r\n'
            'RRULE:FREQ=WEEKLY;COUNT=4\r\nEXDATE:20170117T140000Z\r\nEND:VEVENT\r\n', course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['homework'], 1)
        homework = Homework.objects.get(course=course)
        self.assertEqual([datetime.datetime.fromisoformat(iso) for iso in homework.exception_dates],
                         [datetime.datetime(2017, 1, 17, 14, tzinfo=datetime.timezone.utc)])
        self.assertEqual([start.date() for start, _ in homework.occurrences()],
                         [datetime.date(2017, 1, 10), datetime.date(2017, 1, 24), datetime.date(2017, 1, 31)])

    def test_import_ics_open_ended_repeat_ends_at_the_class_last_day(self):
        # GIVEN
        course = self._given_course()

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:quiz\r\nSUMMARY:Quiz\r\nDTSTART:20170110T140000Z\r\nDTEND:20170110T150000Z\r\n'
            'RRULE:FREQ=WEEKLY;BYDAY=TU\r\nEND:VEVENT\r\n', course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['homework'], 1)
        homework = Homework.objects.get(course=course)
        self.assertEqual(homework.recurrence_rule, 'FREQ=WEEKLY;BYDAY=TU;UNTIL=20170509T065959Z')
        starts = [start for start, _ in homework.occurrences()]
        self.assertEqual((len(starts), starts[-1]), (17, datetime.datetime(2017, 5, 2, 13, tzinfo=datetime.timezone.utc)))

    def test_import_ics_rdate_extras_are_standalone_assignments(self):
        # GIVEN
        course = self._given_course()

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:quiz\r\nSUMMARY:Quiz\r\nDTSTART:20170110T140000Z\r\nDTEND:20170110T150000Z\r\n'
            'RRULE:FREQ=WEEKLY;COUNT=2\r\nRDATE:20170301T140000Z\r\nEND:VEVENT\r\n', course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['homework'], 2)
        extra = Homework.objects.get(course=course, start=datetime.datetime(2017, 3, 1, 14, tzinfo=datetime.timezone.utc))
        self.assertIsNone(extra.recurrence_rule)
        series = Homework.objects.get(course=course, recurrence_rule__isnull=False)
        self.assertEqual(len(list(series.occurrences())), 2)

    def test_import_ics_over_the_cap_names_the_entry_and_saves_nothing(self):
        # GIVEN
        course = self._given_course(end_date=datetime.date(2019, 1, 1))

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:ok\r\nSUMMARY:Weekly quiz\r\nDTSTART:20170110T140000Z\r\n'
            'DTEND:20170110T150000Z\r\nRRULE:FREQ=WEEKLY;COUNT=3\r\nEND:VEVENT\r\n'
            'BEGIN:VEVENT\r\nUID:log\r\nSUMMARY:Daily log\r\nDTSTART:20170110T140000Z\r\n'
            'DTEND:20170110T150000Z\r\nRRULE:FREQ=DAILY\r\nEND:VEVENT\r\n', course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(str(response.data['homework']), '"Daily log": It repeats more than 366 times.')
        self.assertFalse(Homework.objects.filter(course=course).exists())

    def test_import_ics_unexpandable_rule_falls_back_to_one_assignment(self):
        # GIVEN
        course = self._given_course()

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:odd\r\nSUMMARY:Odd\r\nDTSTART:20170110T140000Z\r\nDTEND:20170110T150000Z\r\n'
            'RRULE:FREQ=WEEKLY;BYDAY=XX\r\nEND:VEVENT\r\n', course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['homework'], 1)
        only = Homework.objects.get(course=course)
        self.assertEqual((only.start, only.recurrence_rule),
                         (datetime.datetime(2017, 1, 10, 14, tzinfo=datetime.timezone.utc), None))

    def test_import_ics_recurring_description_links_a_note_to_the_series(self):
        # GIVEN
        course = self._given_course()

        # WHEN
        response = self._post_inline_ics(
            'BEGIN:VEVENT\r\nUID:quiz\r\nSUMMARY:Quiz\r\nDESCRIPTION:Bring a calculator\r\n'
            'DTSTART:20170110T140000Z\r\nDTEND:20170110T150000Z\r\nRRULE:FREQ=WEEKLY;COUNT=3\r\nEND:VEVENT\r\n',
            course)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        notes = list(Homework.objects.get(course=course).notes_set.all())
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].content['ops'][0]['insert'].strip(), 'Bring a calculator')
