import datetime
import io
import json
import zipfile
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.tests.helpers import commonhelper
from helium.common.utils import gradeutils
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, ResourceGroup, Resource, Event, \
    Homework, Reminder, Note
from helium.importexport.tests.helpers import importexporthelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    resourcegrouphelper, resourcehelper, eventhelper, homeworkhelper, attachmenthelper, reminderhelper, notehelper


class TestCaseImportExportViews(APITestCase):
    def test_importexport_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('importexport_import')),
            self.client.post(reverse('importexport_export'))
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def _import_sample_twice(self, as_zip=False):
        content = importexporthelper.given_resource_upload('sample.json').read()

        if as_zip:
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('sample.json', content)
            content, filename = buffer.getvalue(), 'sample.zip'
        else:
            filename = 'sample.json'

        # Uploaded twice so the key IDs do not line up and the remapping is properly tested
        return [importexporthelper.post_import_upload(self.client, SimpleUploadedFile(filename, content))
                for _ in range(2)]

    def _verify_sample_import(self, user, response1, response2):
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {'external_calendars': 1, 'course_groups': 2, 'courses': 2, 'course_schedules': 2, 'categories': 2,
             'resource_groups': 1, 'resources': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 5},
            {key: value for key, value in response1.data.items() if key != 'ids'})
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {'external_calendars': 1, 'course_groups': 2, 'courses': 2, 'course_schedules': 2, 'categories': 2,
             'resource_groups': 1, 'resources': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 5},
            {key: value for key, value in response2.data.items() if key != 'ids'})
        external_calendars = ExternalCalendar.objects.all()
        course_groups = CourseGroup.objects.all()
        courses = Course.objects.all()
        course_schedules = CourseSchedule.objects.all()
        categories = Category.objects.all()
        resource_groups = ResourceGroup.objects.all()
        resources = Resource.objects.all()
        events = Event.objects.all()
        homework = Homework.objects.all()
        reminders = Reminder.objects.all()
        self.assertEqual(len(external_calendars), 2)
        self.assertEqual(len(course_groups), 4)
        self.assertEqual(len(courses), 4)
        self.assertEqual(len(course_schedules), 4)
        self.assertEqual(len(categories), 4)
        self.assertEqual(len(resource_groups), 2)
        self.assertEqual(len(resources), 2)
        self.assertEqual(len(events), 4)
        self.assertEqual(len(homework), 4)
        self.assertEqual(len(reminders), 4)
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendars[1],
                                                                    {'id': 2, 'title': '📅 My Calendar',
                                                                     'url': 'http://go.com/valid-ical-feed',
                                                                     'color': '#fad165', 'shown_on_calendar': True,
                                                                     'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_groups[2], {'overall_grade': 66.6667,
                                                                                    'start_date': '2017-01-06',
                                                                                    'end_date': '2017-05-08',
                                                                                    'shown_on_calendar': True,
                                                                                    'title': '🍂 Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_groups[3], {'overall_grade': -1.0,
                                                                                    'start_date': '2017-01-06',
                                                                                    'end_date': '2017-05-08',
                                                                                    'shown_on_calendar': True,
                                                                                    'title': '🍂 Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursehelper.verify_course_matches_data(self, courses[2], {'title': '🧪 Test Course', 'room': '',
                                                                   'credits': 5.0, 'color': '#4986e7',
                                                                   'website': 'http://mycourse.com', 'is_online': False,
                                                                   'current_grade': 66.6667, 'trend': None,
                                                                   'teacher_name': 'My Teacher',
                                                                   'teacher_email': 'teacher@email.com',
                                                                   'start_date': '2017-01-06', 'end_date': '2017-05-08',
                                                                   'course_group': course_groups[2].pk})
        coursehelper.verify_course_matches_data(self, courses[3],
                                                {'title': '🧪 Test Course', 'room': 'DNC 201', 'credits': 5.0,
                                                 'color': '#4986e7', 'website': 'http://mycourse.com',
                                                 'is_online': False, 'current_grade': -1.0, 'trend': None,
                                                 'teacher_name': 'My Teacher',
                                                 'teacher_email': 'teacher@email.com',
                                                 'start_date': '2017-01-06', 'end_date': '2017-05-08',
                                                 'course_group': course_groups[3].pk})
        courseschedulehelper.verify_course_schedule_matches(self, course_schedules[2], {'days_of_week': '0101010',
                                                                                        'sun_start_time': '12:00:00',
                                                                                        'sun_end_time': '12:00:00',
                                                                                        'mon_start_time': '2:30:00',
                                                                                        'mon_end_time': '3:00:00',
                                                                                        'tue_start_time': '12:00:00',
                                                                                        'tue_end_time': '12:00:00',
                                                                                        'wed_start_time': '2:30:00',
                                                                                        'wed_end_time': '3:00:00',
                                                                                        'thu_start_time': '12:00:00',
                                                                                        'thu_end_time': '12:00:00',
                                                                                        'fri_start_time': '2:30:00',
                                                                                        'fri_end_time': '5:00:00',
                                                                                        'sat_start_time': '12:00:00',
                                                                                        'sat_end_time': '12:00:00',
                                                                                        'course': courses[2].pk})
        courseschedulehelper.verify_course_schedule_matches(self, course_schedules[3], {'days_of_week': '0101010',
                                                                                        'sun_start_time': '12:00:00',
                                                                                        'sun_end_time': '12:00:00',
                                                                                        'mon_start_time': '2:30:00',
                                                                                        'mon_end_time': '3:00:00',
                                                                                        'tue_start_time': '12:00:00',
                                                                                        'tue_end_time': '12:00:00',
                                                                                        'wed_start_time': '2:30:00',
                                                                                        'wed_end_time': '3:00:00',
                                                                                        'thu_start_time': '12:00:00',
                                                                                        'thu_end_time': '12:00:00',
                                                                                        'fri_start_time': '2:30:00',
                                                                                        'fri_end_time': '5:00:00',
                                                                                        'sat_start_time': '12:00:00',
                                                                                        'sat_end_time': '12:00:00',
                                                                                        'course': courses[3].pk})
        categoryhelper.verify_category_matches_data(self, categories[3],
                                                    {'title': '📊 Test Category 1', 'weight': 0.0, 'color': '#4986e7',
                                                     'average_grade': -1.0, 'grade_by_weight': 0.0, 'trend': None,
                                                     'course': courses[3].pk})
        categoryhelper.verify_category_matches_data(self, categories[1],
                                                    {'title': 'Uncategorized', 'weight': 0.0, 'color': '#4986e7',
                                                     'average_grade': 66.6667, 'grade_by_weight': 0.0, 'trend': None,
                                                     'course': courses[2].pk})
        resourcegrouphelper.verify_resource_group_matches_data(self, resource_groups[1],
                                                               {'title': '📚 Test Material Group',
                                                                'shown_on_calendar': True, 'user': user.pk})
        resourcehelper.verify_resource_matches_data(self, resources[1],
                                                    {'title': '📘 Test Material', 'status': 3, 'condition': 7,
                                                     'website': 'http://www.material.com', 'price': '9.99',
                                                     'resource_group': resource_groups[1].pk, 'courses': []})
        self.assertTrue(resources[1].notes_set.exists())
        resource_note = resources[1].notes_set.first()
        self.assertIn('ops', resource_note.content)
        self.assertEqual(resource_note.content['ops'][0]['insert'], 'Return by 7/1')

        eventhelper.verify_event_matches_data(self, events[2],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75,
                                               'owner_id': None, 'user': user.pk})
        eventhelper.verify_event_matches_data(self, events[3],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75,
                                               'owner_id': None, 'user': user.pk})
        self.assertTrue(events[2].notes_set.exists())
        event_note = events[2].notes_set.first()
        self.assertIn('ops', event_note.content)
        self.assertEqual(event_note.content['ops'][0]['insert'], 'A comment on an event.')

        homeworkhelper.verify_homework_matches_data(self, homework[2],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65,
                                                     'current_grade': '20/30',
                                                     'completed': True, 'category': categories[1].pk,
                                                     'course': courses[2].pk, 'resources': [resources[1].pk]})
        homeworkhelper.verify_homework_matches_data(self, homework[3],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65,
                                                     'current_grade': '-1/100',
                                                     'completed': False, 'category': categories[3].pk,
                                                     'course': courses[3].pk, 'resources': []})
        self.assertTrue(homework[2].notes_set.exists())
        homework_note = homework[2].notes_set.first()
        self.assertIn('ops', homework_note.content)
        self.assertEqual(homework_note.content['ops'][0]['insert'], 'A comment on a homework.')

        # 5 linked notes in the sample, uploaded twice
        self.assertEqual(Note.objects.filter(user=user).count(), 10)
        reminderhelper.verify_reminder_matches_data(self, reminders[2], {'id': 1, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45:00Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 3,
                                                                         'sent': False, 'dismissed': False,
                                                                         'homework': homework[0].pk,
                                                                         'event': None, 'user': user.pk})
        reminderhelper.verify_reminder_matches_data(self, reminders[3], {'id': 3, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 3,
                                                                         'sent': False, 'dismissed': False,
                                                                         'homework': homework[2].pk,
                                                                         'event': None, 'user': user.pk})

    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_import_success(self, mock_validate_url):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response1, response2 = self._import_sample_twice()

        # THEN
        self._verify_sample_import(user, response1, response2)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_import_success_from_zip(self, mock_validate_url):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response1, response2 = self._import_sample_twice(as_zip=True)

        # THEN
        self._verify_sample_import(user, response1, response2)

    def test_import_blocks_template_and_provisions_uncategorized(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        import_data = {
            'course_groups': [{
                'id': 1, 'title': 'Test Group', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
                'shown_on_calendar': True, 'overall_grade': '-1', 'user': 1,
            }],
            'courses': [{
                'id': 1, 'title': 'Test Course', 'room': '', 'credits': '3.00', 'color': '#4986e7',
                'website': '', 'is_online': False, 'current_grade': '-1', 'teacher_name': '',
                'teacher_email': '', 'start_date': '2024-01-01', 'end_date': '2024-05-01', 'course_group': 1,
                'template': 0,
            }],
            'categories': [],
        }

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course = Course.objects.get(title='Test Course')
        categories = Category.objects.filter(course=course)
        self.assertEqual(categories.count(), 1)
        self.assertEqual(categories.first().title, 'Uncategorized')

    def test_import_course_with_categories_gets_no_uncategorized(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        import_data = {
            'course_groups': [{
                'id': 1, 'title': 'Test Group', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
                'shown_on_calendar': True, 'overall_grade': '-1', 'user': 1,
            }],
            'courses': [{
                'id': 1, 'title': 'Test Course', 'room': '', 'credits': '3.00', 'color': '#4986e7',
                'website': '', 'is_online': False, 'current_grade': '-1', 'teacher_name': '',
                'teacher_email': '', 'start_date': '2024-01-01', 'end_date': '2024-05-01', 'course_group': 1,
            }],
            'categories': [{
                'id': 1, 'title': 'Homework', 'weight': '0.00', 'average_grade': '-1',
                'grade_by_weight': '0', 'color': '#4986e7', 'course': 1,
            }],
        }

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course = Course.objects.get(title='Test Course')
        categories = Category.objects.filter(course=course)
        self.assertEqual(categories.count(), 1)
        self.assertEqual(categories.first().title, 'Homework')

    def test_import_invalid_json(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        tmp_file = attachmenthelper.given_file_exists(ext='.json')

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Invalid JSON', response.data['details'])
        importexporthelper.verify_nothing_imported(self)

    def test_import_multiple_files_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        uploads = [importexporthelper.given_resource_upload('sample.json') for _ in range(2)]

        # WHEN
        response = self.client.post(reverse('importexport_import'), {'file[]': uploads})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['details'], 'Upload exactly one file per request.')
        importexporthelper.verify_nothing_imported(self)

    def test_import_no_files_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(
            reverse('importexport_import'),
            {},
            format='multipart')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['details'], 'Upload exactly one file per request.')

    def test_import_invalid_relationships(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = importexporthelper.post_import_resource(self.client, 'invalidsample.json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('homework', response.data)
        self.assertIn('Unresolved `course`', str(response.data['homework']))
        importexporthelper.verify_nothing_imported(self)

    def test_export_success(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        external_calendar = externalcalendarhelper.given_external_calendar_exists(user1)
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user2)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user1)
        course_group3 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1, room='')
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group3)
        course_schedule1 = courseschedulehelper.given_course_schedule_exists(course1)
        course_schedule2 = courseschedulehelper.given_course_schedule_exists(course2)
        courseschedulehelper.given_course_schedule_exists(course3)
        category1 = categoryhelper.given_category_exists(course1, title='Uncategorized')
        category2 = categoryhelper.given_category_exists(course2, weight=100)
        category3 = categoryhelper.given_category_exists(course3)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user1)
        resource_group2 = resourcegrouphelper.given_resource_group_exists(user2)
        resource1 = resourcehelper.given_resource_exists(resource_group1)
        resourcehelper.given_resource_exists(resource_group2)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade="20/30", resources=[resource1])
        homework2 = homeworkhelper.given_homework_exists(course2, category=category2, current_grade="-1/100")
        homeworkhelper.given_homework_exists(course3, category=category3, completed=True, current_grade="-1/100")
        reminder = reminderhelper.given_reminder_exists(user1, homework=homework1)

        # WHEN
        response = self.client.get(reverse('importexport_export'))
        data = json.loads(response.content.decode('utf-8'))

        # THEN
        course_group1.refresh_from_db()
        course_group2.refresh_from_db()
        course1.refresh_from_db()
        course2.refresh_from_db()
        category1.refresh_from_db()
        category2.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        externalcalendarhelper.verify_externalcalendar_matches_data(self, external_calendar,
                                                                    data['external_calendars'][0])
        eventhelper.verify_event_matches_data(self, event1, data['events'][0])
        eventhelper.verify_event_matches_data(self, event2, data['events'][1])
        coursegrouphelper.verify_course_group_matches_data(self, course_group1, data['course_groups'][0])
        coursegrouphelper.verify_course_group_matches_data(self, course_group2, data['course_groups'][1])
        coursehelper.verify_course_matches_data(self, course1, data['courses'][0])
        coursehelper.verify_course_matches_data(self, course2, data['courses'][1])
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule1, data['course_schedules'][0])
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule2, data['course_schedules'][1])
        categoryhelper.verify_category_matches_data(self, category1, data['categories'][0])
        categoryhelper.verify_category_matches_data(self, category2, data['categories'][1])
        homeworkhelper.verify_homework_matches_data(self, homework1, data['homework'][0])
        homeworkhelper.verify_homework_matches_data(self, homework2, data['homework'][1])
        reminderhelper.verify_reminder_matches_data(self, reminder, data['reminders'][0])
        # Computed, annotation-backed summary fields are exported but derived read-only, so they are
        # not covered by the verify_*_matches_data helpers; assert them directly to ensure the export
        # reports real values rather than silently defaulting to 0/False
        self.assertEqual(data['courses'][0]['num_homework'], 1)
        self.assertEqual(data['courses'][0]['num_homework_completed'], 1)
        self.assertEqual(data['courses'][0]['num_homework_graded'], 1)
        self.assertFalse(data['courses'][0]['has_weighted_grading'])
        self.assertEqual(data['courses'][1]['num_homework'], 1)
        self.assertEqual(data['courses'][1]['num_homework_completed'], 0)
        self.assertEqual(data['courses'][1]['num_homework_graded'], 0)
        self.assertTrue(data['courses'][1]['has_weighted_grading'])
        self.assertEqual(data['course_groups'][0]['num_homework'], 1)
        self.assertEqual(data['course_groups'][0]['num_homework_completed'], 1)
        self.assertEqual(data['course_groups'][0]['num_homework_graded'], 1)
        self.assertEqual(data['course_groups'][1]['num_homework'], 1)
        self.assertEqual(data['course_groups'][1]['num_homework_completed'], 0)
        self.assertEqual(data['course_groups'][1]['num_homework_graded'], 0)
        self.assertEqual(data['categories'][0]['num_homework'], 1)
        self.assertEqual(data['categories'][0]['num_homework_completed'], 1)
        self.assertEqual(data['categories'][0]['num_homework_graded'], 1)
        self.assertEqual(data['categories'][1]['num_homework'], 1)
        self.assertEqual(data['categories'][1]['num_homework_completed'], 0)
        self.assertEqual(data['categories'][1]['num_homework_graded'], 0)

    def test_export_import_preserves_event_recurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(
            user,
            title='♻️ Recurring Event',
            recurrence_rule='FREQ=WEEKLY;BYDAY=MO,WE,FR',
            exception_dates=['2017-05-15T12:00:00Z', '2017-05-22T12:00:00Z'],
        )

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(len(export_data['events']), 1)
        self.assertEqual(export_data['events'][0]['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO,WE,FR')
        self.assertEqual(
            export_data['events'][0]['exception_dates'],
            ['2017-05-15T12:00:00Z', '2017-05-22T12:00:00Z'],
        )

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_rrule_roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        events = Event.objects.filter(user=user).order_by('pk')
        self.assertEqual(events.count(), 2)
        imported = events.last()
        eventhelper.verify_event_matches_data(
            self,
            imported,
            {
                'title': '♻️ Recurring Event',
                'all_day': False,
                'show_end_time': True,
                'start': '2017-05-08T12:00:00Z',
                'end': '2017-05-08T14:00:00Z',
                'priority': 75,
                'owner_id': '12345',
                'recurrence_rule': 'FREQ=WEEKLY;BYDAY=MO,WE,FR',
                'exception_dates': ['2017-05-15T12:00:00Z', '2017-05-22T12:00:00Z'],
                'user': user.pk,
            },
        )

    def test_import_drops_recurrence_rule_sfcalendar_cannot_expand_instead_of_failing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        eventhelper.given_event_exists(user, title='Monthly series', recurrence_rule='FREQ=MONTHLY;BYDAY=MO,WE')
        eventhelper.given_event_exists(user, title='Hourly series', recurrence_rule='FREQ=DAILY;BYHOUR=9,15',
                                       exception_dates=['2017-05-09T12:00:00Z'])
        export_data = importexporthelper.get_export_data(self, verify_status=False)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_unsupported_rrule.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        for title in ('Monthly series', 'Hourly series'):
            imported = Event.objects.filter(user=user, title=title).order_by('pk').last()
            self.assertIsNone(imported.recurrence_rule, 'the event is kept as a single occurrence')
            self.assertIsNone(imported.exception_dates)

    def test_export_import_preserves_homework_recurrence(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homeworkhelper.given_homework_exists(
            course,
            start=datetime.datetime(2017, 4, 17, 16, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2017, 4, 17, 18, 0, 0, tzinfo=datetime.timezone.utc),
            recurrence_rule='FREQ=WEEKLY;BYDAY=MO;UNTIL=20170508T235959Z',
            exception_dates=['2017-04-24T16:00:00Z'])

        # WHEN
        export_data = importexporthelper.get_export_data(self, verify_status=False)
        import_response = importexporthelper.post_import(self.client, export_data, filename='_homework_rrule_roundtrip.json')

        # THEN
        self.assertEqual(export_data['homework'][0]['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20170508T235959Z')
        self.assertEqual(export_data['homework'][0]['exception_dates'], ['2017-04-24T16:00:00Z'])
        self.assertEqual(import_response.status_code, status.HTTP_200_OK, import_response.data)
        imported = Homework.objects.for_user(user.pk).order_by('pk').last()
        self.assertNotEqual(imported.course_id, course.pk)
        self.assertEqual(imported.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20170508T235959Z')
        self.assertEqual(imported.exception_dates, ['2017-04-24T16:00:00Z'])

    def test_import_with_an_unsupported_homework_recurrence_rule_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user))
        homeworkhelper.given_homework_exists(course, recurrence_rule='FREQ=MONTHLY;BYDAY=MO,WE')
        export_data = importexporthelper.get_export_data(self, verify_status=False)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_unsupported_homework_rrule.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(f"homework id {export_data['homework'][0]['id']}, recurrence_rule",
                      str(import_response.data['homework']))
        self.assertEqual(Homework.objects.for_user(user.pk).count(), 1)

    def test_import_with_a_homework_repeating_too_often_names_the_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course = coursehelper.given_course_exists(coursegrouphelper.given_course_group_exists(user),
                                                  end_date=datetime.date(2019, 5, 8))
        homeworkhelper.given_homework_exists(course, recurrence_rule='FREQ=DAILY')
        export_data = importexporthelper.get_export_data(self, verify_status=False)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_too_many_occurrences.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual([f"homework id {export_data['homework'][0]['id']}, recurrence_rule: It repeats more than "
                          f"366 times."], [str(message) for message in import_response.data['homework']])
        self.assertEqual(Homework.objects.for_user(user.pk).count(), 1)

    def test_export_import_preserves_multiple_schedules_per_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0101010')
        courseschedulehelper.given_course_schedule_exists(course, days_of_week='0010100')

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(len(export_data['course_schedules']), 2)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_multi_schedule_roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        self.assertEqual(import_response.data['course_schedules'], 2)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported_schedules = CourseSchedule.objects.filter(course=imported_course).order_by('pk')
        self.assertEqual(len(imported_schedules), 2)
        self.assertEqual({s.days_of_week for s in imported_schedules}, {'0101010', '0010100'})

    def test_export_import_preserves_class_note_link(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        notehelper.given_note_linked_to_course(user, course, title='Class Note')

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(export_data['notes'][0]['courses'], [course.pk])

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_class_note_roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported_note = Note.objects.get(courses=imported_course)
        self.assertEqual(imported_note.title, 'Class Note')

    def test_export_import_preserves_cycle_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_cycle_schedule_exists(
            course, cycle_length=6, anchor_date=datetime.date(2026, 3, 2),
            cycle_slots=[{'indices': [1, 3], 'start_time': '09:00:00', 'end_time': '09:50:00'}])

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(len(export_data['course_schedules']), 1)
        self.assertEqual(export_data['course_schedules'][0]['cycle_length'], 6)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported = CourseSchedule.objects.get(course=imported_course)
        self.assertEqual(imported.cycle_length, 6)
        self.assertEqual(imported.anchor_date, datetime.date(2026, 3, 2))
        self.assertEqual(imported.cycle_slots,
                         [{'indices': [1, 3], 'start_time': '09:00:00', 'end_time': '09:50:00'}])

    def test_export_import_preserves_week_based_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_week_based_schedule_exists(
            course, days_of_week='0100000', week_offset=1, anchor_date=datetime.date(2026, 3, 2))

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(len(export_data['course_schedules']), 1)
        self.assertTrue(export_data['course_schedules'][0]['is_week_based'])
        self.assertEqual(export_data['course_schedules'][0]['week_offset'], 1)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported = CourseSchedule.objects.get(course=imported_course)
        self.assertTrue(imported.is_week_based)
        self.assertEqual(imported.week_offset, 1)
        self.assertEqual(imported.anchor_date, datetime.date(2026, 3, 2))

    def test_export_import_preserves_schedule_date_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_course_schedule_exists(course)
        schedule.start_date = datetime.date(2026, 3, 9)
        schedule.end_date = datetime.date(2026, 4, 24)
        schedule.save()

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(export_data['course_schedules'][0]['start_date'], '2026-03-09')
        self.assertEqual(export_data['course_schedules'][0]['end_date'], '2026-04-24')

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported = CourseSchedule.objects.get(course=imported_course)
        self.assertEqual(imported.start_date, datetime.date(2026, 3, 9))
        self.assertEqual(imported.end_date, datetime.date(2026, 4, 24))

    def test_export_import_preserves_schedule_exceptions(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_course_schedule_exists(course)
        schedule.exceptions = '20170215,20170301'
        schedule.save()

        # WHEN
        export_data = importexporthelper.get_export_data(self)
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(export_data['course_schedules'][0]['exceptions'], '20170215,20170301')
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        self.assertEqual(CourseSchedule.objects.get(course=imported_course).exceptions, '20170215,20170301')

    def test_export_import_keeps_a_schedule_cancellation_left_outside_its_window(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_course_schedule_exists(course)
        schedule.end_date = datetime.date(2017, 2, 28)
        schedule.exceptions = '20170301'
        schedule.save()

        # WHEN
        export_data = importexporthelper.get_export_data(self)
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        self.assertEqual(CourseSchedule.objects.get(course=imported_course).exceptions, '20170301')

    def test_export_import_preserves_schedule_template(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule = courseschedulehelper.given_cycle_schedule_exists(course)
        schedule.template = enums.AB_DAY
        schedule.save()

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(export_data['course_schedules'][0]['template'], enums.AB_DAY)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        imported_course = Course.objects.exclude(pk=course.pk).get(course_group__user=user)
        imported = CourseSchedule.objects.get(course=imported_course)
        self.assertEqual(imported.template, enums.AB_DAY)
        self.assertEqual(imported.cycle_length, 2)

    def test_export_import_preserves_homework_completed_at(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        homework = homeworkhelper.given_homework_exists(course, category=category, completed=True,
                                                        current_grade='90/100')
        original_completed_at = datetime.datetime(2017, 3, 1, 9, 30, tzinfo=datetime.timezone.utc)
        Homework.objects.filter(pk=homework.pk).update(completed_at=original_completed_at)

        # WHEN
        export_data = importexporthelper.get_export_data(self)

        # THEN
        self.assertEqual(len(export_data['homework']), 1)
        self.assertEqual(parse_datetime(export_data['homework'][0]['completed_at']), original_completed_at)

        # WHEN
        import_response = importexporthelper.post_import(self.client, export_data, filename='_completed_at_roundtrip.json')

        # THEN
        self.assertEqual(import_response.status_code, status.HTTP_200_OK)
        homework_qs = Homework.objects.for_user(user.pk).order_by('pk')
        self.assertEqual(homework_qs.count(), 2)
        self.assertEqual(homework_qs.last().completed_at, original_completed_at)

    def test_import_ignores_time_zone_in_an_uploaded_payload(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Asia/Tokyo')
        payload = {
            'time_zone': 'America/Chicago',
            'course_groups': [{'id': 1, 'title': 'Group', 'start_date': '2026-01-05',
                               'end_date': '2026-05-08', 'shown_on_calendar': True}],
            'courses': [{'id': 1, 'title': 'Course', 'credits': 3.0, 'color': '#4986e7',
                         'start_date': '2026-01-05', 'end_date': '2026-05-08',
                         'course_group': 1}],
            'course_schedules': [{'id': 1, 'days_of_week': '0101010', 'course': 1,
                                  'sun_start_time': '11:00:00', 'sun_end_time': '11:50:00',
                                  'mon_start_time': '11:00:00', 'mon_end_time': '11:50:00',
                                  'tue_start_time': '11:00:00', 'tue_end_time': '11:50:00',
                                  'wed_start_time': '11:00:00', 'wed_end_time': '11:50:00',
                                  'thu_start_time': '11:00:00', 'thu_end_time': '11:50:00',
                                  'fri_start_time': '11:00:00', 'fri_end_time': '11:50:00',
                                  'sat_start_time': '11:00:00', 'sat_end_time': '11:50:00'}],
            'homework': [{'id': 1, 'title': 'Quiz', 'all_day': False, 'show_end_time': True,
                          'start': '2026-01-07T16:00:00Z', 'end': '2026-01-07T16:30:00Z',
                          'current_grade': '-1/100', 'completed': False, 'course': 1}],
        }

        # WHEN
        response = importexporthelper.post_import(self.client, payload, filename='payload.json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, msg=response.data)
        self.assertEqual(CourseSchedule.objects.get().mon_start_time, datetime.time(11, 0))
        self.assertEqual(Homework.objects.get().start,
                         datetime.datetime(2026, 1, 7, 16, 0, tzinfo=datetime.timezone.utc))

    def test_import_notes_with_direct_entity_links(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        import_data = {
            'course_groups': [{
                'id': 1,
                'title': 'Test Group',
                'start_date': '2024-01-01',
                'end_date': '2024-05-01',
                'shown_on_calendar': True,
                'overall_grade': '-1',
                'user': 1
            }],
            'courses': [{
                'id': 1,
                'title': 'Test Course',
                'room': '',
                'credits': '3.00',
                'color': '#4986e7',
                'website': '',
                'is_online': False,
                'current_grade': '-1',
                'teacher_name': '',
                'teacher_email': '',
                'start_date': '2024-01-01',
                'end_date': '2024-05-01',
                'course_group': 1
            }],
            'categories': [{
                'id': 1,
                'title': 'Homework',
                'weight': '100.00',
                'average_grade': '-1',
                'grade_by_weight': '0',
                'color': '#4986e7',
                'course': 1
            }],
            'resource_groups': [{
                'id': 1,
                'title': 'Test Materials',
                'shown_on_calendar': True,
                'user': 1
            }],
            'resources': [{
                'id': 100,
                'title': 'Test Textbook',
                'status': 0,
                'condition': 0,
                'website': '',
                'price': '$50.00',
                'resource_group': 1,
                'courses': [1]
            }],
            'events': [{
                'id': 200,
                'title': 'Study Session',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-01T10:00:00Z',
                'end': '2024-02-01T11:00:00Z',
                'priority': 50,
                'user': 1
            }],
            'homework': [{
                'id': 300,
                'title': 'Assignment 1',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-15T10:00:00Z',
                'end': '2024-02-15T12:00:00Z',
                'priority': 50,
                'current_grade': '-1/100',
                'completed': False,
                'category': 1,
                'resources': [100],
                'course': 1
            }],
            'reminders': [],
            'course_schedules': [],
            'notes': [
                {
                    'id': 1,
                    'title': 'Textbook ISBN',
                    'content': {'ops': [{'insert': 'ISBN: 978-1234567890\n'}]},
                    'homework': [],
                    'events': [],
                    'resources': [100]
                },
                {
                    'id': 2,
                    'title': 'Study Topics',
                    'content': {
                        'ops': [
                            {'insert': 'Topics to review:\n'},
                            {'insert': 'Chapter 1'},
                            {'insert': '\n', 'attributes': {'list': 'bullet'}},
                            {'insert': 'Chapter 2'},
                            {'insert': '\n', 'attributes': {'list': 'bullet'}}
                        ]
                    },
                    'homework': [],
                    'events': [200],
                    'resources': []
                },
                {
                    'id': 3,
                    'title': 'Assignment Notes',
                    'content': {
                        'ops': [
                            {'insert': 'Remember to cite sources'},
                            {'insert': '\n', 'attributes': {'list': 'checked'}},
                            {'insert': 'Double-check math'},
                            {'insert': '\n', 'attributes': {'list': 'unchecked'}}
                        ]
                    },
                    'homework': [300],
                    'events': [],
                    'resources': []
                },
                {
                    'id': 4,
                    'title': 'Standalone Note',
                    'content': {'ops': [{'insert': 'General study tips\n'}]},
                    'homework': [],
                    'events': [],
                    'resources': []
                }
            ]
        }

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Note.objects.count(), 4)

        resource = Resource.objects.first()
        textbook_note = Note.objects.get(title='Textbook ISBN')
        self.assertTrue(textbook_note.resources.filter(pk=resource.pk).exists())

        event = Event.objects.first()
        study_note = Note.objects.get(title='Study Topics')
        self.assertTrue(study_note.events.filter(pk=event.pk).exists())

        homework = Homework.objects.first()
        assignment_note = Note.objects.get(title='Assignment Notes')
        self.assertTrue(assignment_note.homework.filter(pk=homework.pk).exists())

        standalone_note = Note.objects.get(title='Standalone Note')
        self.assertFalse(standalone_note.homework.exists())
        self.assertFalse(standalone_note.events.exists())
        self.assertFalse(standalone_note.resources.exists())

    def _minimal_import_payload(self):
        return {
            'course_groups': [{
                'id': 1, 'title': 'G', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
                'shown_on_calendar': True, 'overall_grade': '-1', 'user': 1,
            }],
            'courses': [{
                'id': 1, 'title': 'C', 'room': '', 'credits': '3.00', 'color': '#4986e7',
                'website': '', 'is_online': False, 'current_grade': '-1', 'teacher_name': '',
                'teacher_email': '', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
                'course_group': 1,
            }],
            'categories': [{
                'id': 1, 'title': 'Default', 'weight': '0.00', 'average_grade': '-1',
                'grade_by_weight': '0', 'color': '#4986e7', 'course': 1,
            }],
            'resource_groups': [{
                'id': 1, 'title': 'MG', 'shown_on_calendar': True, 'user': 1,
            }],
            'resources': [{
                'id': 1, 'title': 'M', 'status': 0, 'condition': 0, 'website': '',
                'price': '', 'resource_group': 1, 'courses': [],
            }],
            'events': [],
            'homework': [],
            'reminders': [],
            'notes': [],
            'course_schedules': [],
        }

    @mock.patch('helium.importexport.views.apis.importviews.reminderservice.process_push_reminders')
    def test_dry_run_validates_without_keeping_anything(self, mock_process_push_reminders):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()

        # WHEN
        with self.captureOnCommitCallbacks() as callbacks:
            response = importexporthelper.post_import(self.client, payload, filename='dry_run.json', dry_run='true')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual((1, 1, 1, 1, 1), (response.data['course_groups'], response.data['courses'],
                                           response.data['categories'], response.data['resource_groups'],
                                           response.data['resources']))
        self.assertNotIn('ids', response.data)
        self.assertFalse(CourseGroup.objects.exists())
        self.assertFalse(Course.objects.exists())
        self.assertFalse(Resource.objects.exists())
        self.assertEqual([], callbacks)
        mock_process_push_reminders.assert_not_called()

    def test_dry_run_reports_the_same_errors_as_an_import(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'][0]['credits'] = 'three'

        # WHEN
        dry_run = importexporthelper.post_import(self.client, payload, filename='dry_run.json', dry_run='true')
        imported = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(dry_run.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(imported.data, dry_run.data)

    def test_import_returns_the_assigned_ids(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()

        # WHEN
        with self.captureOnCommitCallbacks() as callbacks:
            response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = response.data['ids']
        self.assertEqual(CourseGroup.objects.get(user=user).pk, ids['course_groups']['1'])
        self.assertEqual(Course.objects.get(course_group__user=user).pk, ids['courses']['1'])
        self.assertEqual(Category.objects.get(course__course_group__user=user, title='Default').pk,
                         ids['categories']['1'])
        self.assertEqual(ResourceGroup.objects.get(user=user).pk, ids['resource_groups']['1'])
        self.assertEqual(Resource.objects.get(resource_group__user=user).pk, ids['resources']['1'])
        self.assertEqual({}, ids['events'])
        self.assertEqual({}, ids['homework'])
        self.assertTrue(callbacks)

    def test_import_into_an_existing_course_group(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        payload = self._minimal_import_payload()

        # WHEN
        response = importexporthelper.post_import(self.client, payload, course_group=course_group.pk)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual((0, 1), (response.data['course_groups'], response.data['courses']))
        self.assertEqual([course_group.pk], list(CourseGroup.objects.for_user(user.pk).values_list('pk', flat=True)))
        course = Course.objects.get(pk=response.data['ids']['courses']['1'])
        self.assertEqual(course_group.pk, course.course_group_id)
        self.assertTrue(Category.objects.filter(course=course, title='Default').exists())

    def test_import_into_another_users_course_group_is_refused(self):
        # GIVEN
        other_user = userhelper.given_a_user_exists(username='other', email='other@heliumedu.com')
        course_group = coursegrouphelper.given_course_group_exists(other_user)
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()

        # WHEN
        responses = [importexporthelper.post_import(self.client, payload, course_group=course_group_id)
                     for course_group_id in (course_group.pk, 'term')]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('course_group', response.data)
        self.assertFalse(Course.objects.exists())
        self.assertEqual(1, CourseGroup.objects.count())

    def test_rejected_import_lists_every_row_error_in_the_section(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        second_course = dict(payload['courses'][0], id=2, credits='-4')
        payload['courses'][0]['credits'] = 'three'
        payload['courses'].append(second_course)

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(2, len(response.data['courses']))
        self.assertTrue(response.data['courses'][0].startswith('courses id 1, credits: '))
        self.assertTrue(response.data['courses'][1].startswith('courses id 2, credits: '))
        self.assertFalse(Course.objects.exists())

    def test_import_note_invalid_payload_rejects_whole_import(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['events'] = [{
            'id': 10, 'title': 'E', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T11:00:00Z', 'priority': 50,
        }]
        payload['homework'] = [{
            'id': 20, 'title': 'H', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T12:00:00Z', 'priority': 50,
            'current_grade': '-1/100', 'completed': False, 'category': 1, 'resources': [],
            'course': 1,
        }]
        payload['notes'] = [{
            'id': 1, 'title': 'Bad', 'content': {'ops': [{'insert': 'x\n'}]},
            'homework': [20], 'events': [10], 'resources': [],
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('notes', response.data)
        self.assertIsInstance(response.data['notes'], list)
        self.assertIn('notes id 1, ', str(response.data['notes'][0]))
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Note.objects.count(), 0)

    def test_import_unresolved_course_group_returns_400_not_500(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'][0]['course_group'] = 999

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('Unresolved `course_group`', str(response.data['courses']))
        self.assertEqual(Course.objects.count(), 0)

    def test_import_unresolved_course_on_category_returns_400_not_500(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['categories'][0]['course'] = 999

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('categories', response.data)
        self.assertIn('Unresolved `course`', str(response.data['categories']))

    def test_import_unresolved_course_on_schedule_returns_400_not_500(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_schedules'] = [{
            'id': 1, 'days_of_week': '0101010',
            'sun_start_time': '00:00:00', 'sun_end_time': '00:00:00',
            'mon_start_time': '10:00:00', 'mon_end_time': '10:50:00',
            'tue_start_time': '00:00:00', 'tue_end_time': '00:00:00',
            'wed_start_time': '10:00:00', 'wed_end_time': '10:50:00',
            'thu_start_time': '00:00:00', 'thu_end_time': '00:00:00',
            'fri_start_time': '10:00:00', 'fri_end_time': '10:50:00',
            'sat_start_time': '00:00:00', 'sat_end_time': '00:00:00',
            'course': 999,
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course_schedules', response.data)
        self.assertIn('Unresolved `course`', str(response.data['course_schedules']))

    def test_import_row_field_error_names_section_and_id(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        del payload['courses'][0]['start_date']
        del payload['courses'][0]['end_date']

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        errors = response.data['courses']
        self.assertIsInstance(errors, list)
        self.assertIn('courses id 1, start_date: This field is required.', errors)
        self.assertIn('courses id 1, end_date: This field is required.', errors)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)

    def test_import_duplicate_id_within_section_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'].append({**payload['courses'][0], 'title': 'C2'})

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('Duplicate id', str(response.data['courses']))

    def test_import_non_integer_id_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'][0]['id'] = {'oops': 'not-an-id'}

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('not a valid id', str(response.data['courses']))

    def test_import_string_int_id_coerced(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_groups'][0]['id'] = '1'
        payload['courses'][0]['id'] = '1'
        payload['courses'][0]['course_group'] = '1'

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Course.objects.count(), 1)

    def test_import_missing_id_in_section_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        del payload['courses'][0]['id']

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('missing required key `id`', str(response.data['courses']))

    def test_import_top_level_resources_succeeds(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Resource.objects.count(), 1)

    def test_import_homework_unresolved_resource_returns_400(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['homework'] = [{
            'id': 10, 'title': 'H', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T12:00:00Z', 'priority': 50,
            'current_grade': '-1/100', 'completed': False, 'category': 1,
            'resources': [9999],
            'course': 1,
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('homework', response.data)
        self.assertIn('Unresolved `resources`', str(response.data['homework']))

    def _import_payload_with_reminder(self, sent, dismissed):
        payload = self._minimal_import_payload()
        payload['events'] = [{
            'id': 10, 'title': 'E', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T11:00:00Z', 'priority': 50,
        }]
        payload['reminders'] = [{
            'id': 20, 'message': 'm', 'offset': 30, 'offset_type': enums.MINUTES,
            'type': enums.PUSH, 'sent': sent, 'dismissed': dismissed,
            'homework': None, 'event': 10, 'course': None,
        }]
        return payload

    def test_import_reminder_dismissed_without_sent_is_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._import_payload_with_reminder(sent=False, dismissed=True)

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reminders', response.data)
        self.assertEqual(Reminder.objects.count(), 0)

    def test_import_reminder_sent_and_dismissed_is_preserved(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._import_payload_with_reminder(sent=True, dismissed=True)

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        reminder = Reminder.objects.get()
        self.assertTrue(reminder.sent)
        self.assertTrue(reminder.dismissed)

    def test_import_duplicate_active_course_series_is_deduped(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['reminders'] = [
            {'id': 1, 'message': 'Heads up', 'offset': 30, 'offset_type': enums.MINUTES,
             'type': enums.PUSH, 'sent': False, 'dismissed': False, 'course': 1},
            {'id': 2, 'message': 'Different text', 'offset': 30, 'offset_type': enums.MINUTES,
             'type': enums.PUSH, 'sent': False, 'dismissed': False, 'course': 1},
        ]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Reminder.objects.filter(course__isnull=False, sent=False,
                                                  dismissed=False).count(), 1)

    def test_import_course_series_with_distinct_offsets_are_both_kept(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['reminders'] = [
            {'id': 1, 'message': 'Heads up', 'offset': 30, 'offset_type': enums.MINUTES,
             'type': enums.PUSH, 'sent': False, 'dismissed': False, 'course': 1},
            {'id': 2, 'message': 'Heads up', 'offset': 45, 'offset_type': enums.MINUTES,
             'type': enums.PUSH, 'sent': False, 'dismissed': False, 'course': 1},
        ]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Reminder.objects.filter(course__isnull=False, sent=False,
                                                  dismissed=False).count(), 2)

    def test_import_round_trips_a_custom_grade_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        custom_scale = [{'min_grade': 0.0, 'grade_point': 0.0, 'label': 'N'},
                        {'min_grade': 50.0, 'grade_point': 1.0, 'label': 'P'}]
        import_data = {
            'course_groups': [{
                'id': 1, 'title': 'Custom', 'start_date': '2024-01-01', 'end_date': '2024-05-01',
                'shown_on_calendar': True, 'overall_grade': '-1', 'user': 1, 'grade_scale': custom_scale,
                'grade_scale_template': None, 'gpa': '3.2000',
            }],
        }

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        custom = CourseGroup.objects.get(user=user, title='Custom')
        self.assertEqual(custom.grade_scale, custom_scale)
        self.assertIsNone(custom.grade_scale_template)
        self.assertEqual(float(custom.gpa), -1)

    def test_import_rejects_a_template_that_conflicts_with_its_grade_scale(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_groups'][0].update(grade_scale_template=enums.GRADE_SCALE_4_5,
                                           grade_scale=gradeutils.preset_grade_scale(enums.GRADE_SCALE_4_0))

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CourseGroup.objects.exists())

    def test_import_round_trips_a_class_grade_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_groups'][0]['grade_scale_template'] = enums.GRADE_SCALE_4_0_PLUS_MINUS
        payload['courses'][0]['grade_scale_template'] = enums.GRADE_SCALE_4_0

        # WHEN
        response = importexporthelper.post_import(self.client, payload)
        exported = self.client.get(reverse('importexport_export'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Course.objects.get(course_group__user=user).grade_scale_template, enums.GRADE_SCALE_4_0)
        self.assertEqual(json.loads(exported.content)['courses'][0]['grade_scale_template'], enums.GRADE_SCALE_4_0)

    def test_import_rejects_a_class_grade_scale_that_does_not_fit_its_group(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_groups'][0]['grade_scale_template'] = enums.GRADE_SCALE_4_0
        payload['courses'][0]['grade_scale_template'] = enums.GRADE_SCALE_10_0

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses id 1, grade_scale_template', str(response.data))
        self.assertFalse(CourseGroup.objects.exists())

    def test_import_rejects_a_template_that_conflicts_with_its_schedule(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_schedules'] = [{
            'id': 1, 'course': 1, 'days_of_week': '0000000', 'template': enums.AB_DAY, 'cycle_length': 6,
            'anchor_date': '2024-01-08',
            'cycle_slots': [{'indices': [1, 2], 'start_time': '09:00:00', 'end_time': '09:50:00'}],
        }]

        # WHEN
        response = importexporthelper.post_import(self.client, payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(CourseGroup.objects.exists())

    def test_imported_group_without_a_scale_has_none_when_the_account_has_no_groups(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        import_data = {'course_groups': [{'id': 1, 'title': 'Term', 'start_date': '2026-01-01',
                                          'end_date': '2026-05-01', 'shown_on_calendar': True}]}

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.get(user=user).grade_scale_template, enums.GRADE_SCALE_NONE)

    def test_imported_group_without_a_scale_inherits_the_most_recent_groups_scale(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        coursegrouphelper.given_course_group_exists(user, start_date=datetime.date(2025, 1, 6),
                                                    grade_scale_template=enums.GRADE_SCALE_4_5)
        import_data = {'course_groups': [{'id': 1, 'title': 'Term', 'start_date': '2026-01-01',
                                          'end_date': '2026-05-01', 'shown_on_calendar': True}]}

        # WHEN
        response = importexporthelper.post_import(self.client, import_data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.get(user=user, title='Term').grade_scale_template, enums.GRADE_SCALE_4_5)
