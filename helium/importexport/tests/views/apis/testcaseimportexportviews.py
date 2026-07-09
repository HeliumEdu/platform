__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import os
from unittest import mock
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, MaterialGroup, Material, Event, \
    Homework, Reminder, Note
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    materialgrouphelper, materialhelper, eventhelper, homeworkhelper, attachmenthelper, reminderhelper


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
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('helium.feed.services.icalexternalcalendarservice.validate_url')
    def test_import_success(self, mock_validate_url):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        with open(os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response1 = self.client.post(
                reverse('importexport_import'),
                data)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {'external_calendars': 1, 'course_groups': 2, 'courses': 2, 'course_schedules': 2, 'categories': 2,
             'resource_groups': 1, 'resources': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 0}, response1.data)
        # We are intentionally uploading this file twice so that, in the case of unit tests, the key IDs do not line
        # up and the remapping is properly tested
        with open(os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response2 = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {'external_calendars': 1, 'course_groups': 2, 'courses': 2, 'course_schedules': 2, 'categories': 2,
             'resource_groups': 1, 'resources': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 0}, response2.data)
        external_calendars = ExternalCalendar.objects.all()
        course_groups = CourseGroup.objects.all()
        courses = Course.objects.all()
        course_schedules = CourseSchedule.objects.all()
        categories = Category.objects.all()
        material_groups = MaterialGroup.objects.all()
        materials = Material.objects.all()
        events = Event.objects.all()
        homework = Homework.objects.all()
        reminders = Reminder.objects.all()
        self.assertEqual(len(external_calendars), 2)
        self.assertEqual(len(course_groups), 4)
        self.assertEqual(len(courses), 4)
        self.assertEqual(len(course_schedules), 4)
        self.assertEqual(len(categories), 4)
        self.assertEqual(len(material_groups), 2)
        self.assertEqual(len(materials), 2)
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
                                                                                    'private_slug': None,
                                                                                    'shown_on_calendar': True,
                                                                                    'title': '🍂 Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_groups[3], {'overall_grade': -1.0,
                                                                                    'start_date': '2017-01-06',
                                                                                    'end_date': '2017-05-08',
                                                                                    'private_slug': None,
                                                                                    'shown_on_calendar': True,
                                                                                    'title': '🍂 Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursehelper.verify_course_matches_data(self, courses[2], {'title': '🧪 Test Course', 'room': '',
                                                                   'credits': 5.0, 'color': '#4986e7',
                                                                   'website': 'http://mycourse.com', 'is_online': False,
                                                                   'current_grade': 66.6667, 'trend': None,
                                                                   'private_slug': None, 'teacher_name': 'My Teacher',
                                                                   'teacher_email': 'teacher@email.com',
                                                                   'start_date': '2017-01-06', 'end_date': '2017-05-08',
                                                                   'course_group': course_groups[2].pk})
        coursehelper.verify_course_matches_data(self, courses[3],
                                                {'title': '🧪 Test Course', 'room': 'DNC 201', 'credits': 5.0,
                                                 'color': '#4986e7', 'website': 'http://mycourse.com',
                                                 'is_online': False, 'current_grade': -1.0, 'trend': None,
                                                 'private_slug': None, 'teacher_name': 'My Teacher',
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
        materialgrouphelper.verify_material_group_matches_data(self, material_groups[1],
                                                               {'title': '📚 Test Material Group',
                                                                'shown_on_calendar': True, 'user': user.pk})
        materialhelper.verify_material_matches_data(self, materials[1],
                                                    {'title': '📘 Test Material', 'status': 3, 'condition': 7,
                                                     'website': 'http://www.material.com', 'price': '9.99',
                                                     'details': 'Return by 7/1',  # Legacy field preserved on import
                                                     'material_group': material_groups[1].pk, 'courses': []})
        # Verify legacy 'details' was converted to Note
        self.assertTrue(materials[1].notes_set.exists())
        material_note = materials[1].notes_set.first()
        self.assertIn('ops', material_note.content)
        self.assertEqual(material_note.content['ops'][0]['insert'], 'Return by 7/1')

        eventhelper.verify_event_matches_data(self, events[2],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': 'A comment on an event.',
                                               'owner_id': None, 'user': user.pk})
        eventhelper.verify_event_matches_data(self, events[3],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': 'A comment on an event.',
                                               'owner_id': None, 'user': user.pk})
        self.assertTrue(events[2].notes_set.exists())
        event_note = events[2].notes_set.first()
        self.assertIn('ops', event_note.content)
        self.assertEqual(event_note.content['ops'][0]['insert'], 'A comment on an event.')

        homeworkhelper.verify_homework_matches_data(self, homework[2],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': 'A comment on a homework.',
                                                     'current_grade': '20/30',
                                                     'completed': True, 'category': categories[1].pk,
                                                     'course': courses[2].pk, 'materials': [materials[1].pk]})
        homeworkhelper.verify_homework_matches_data(self, homework[3],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': 'A comment on a homework.',
                                                     'current_grade': '-1/100',
                                                     'completed': False, 'category': categories[3].pk,
                                                     'course': courses[3].pk, 'materials': []})
        self.assertTrue(homework[2].notes_set.exists())
        homework_note = homework[2].notes_set.first()
        self.assertIn('ops', homework_note.content)
        self.assertEqual(homework_note.content['ops'][0]['insert'], 'A comment on a homework.')

        # Verify total Note counts (4 events + 4 homework + 2 materials = 10 with legacy content)
        # But we import twice, so 2x that, but items with empty comments don't create notes
        # Events: 4 with comments, Homework: 4 with comments, Materials: 2 with details
        self.assertEqual(Note.objects.filter(user=user).count(), 10)
        reminderhelper.verify_reminder_matches_data(self, reminders[2], {'id': 1, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45:00Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 2,
                                                                         'sent': False, 'dismissed': False,
                                                                         'homework': homework[0].pk,
                                                                         'event': None, 'user': user.pk})
        reminderhelper.verify_reminder_matches_data(self, reminders[3], {'id': 3, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 2,
                                                                         'sent': False, 'dismissed': False,
                                                                         'homework': homework[2].pk,
                                                                         'event': None, 'user': user.pk})

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
        self.assertEqual(ExternalCalendar.objects.count(), 0)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(CourseSchedule.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MaterialGroup.objects.count(), 0)
        self.assertEqual(Material.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Reminder.objects.count(), 0)

    def test_import_multiple_files_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        sample_path = os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'sample.json'))

        # WHEN
        with open(sample_path) as fp1, open(sample_path) as fp2:
            data = {
                'file[]': [fp1, fp2]
            }
            response = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['details'], 'Upload exactly one file per request.')
        self.assertEqual(ExternalCalendar.objects.count(), 0)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(CourseSchedule.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MaterialGroup.objects.count(), 0)
        self.assertEqual(Material.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Reminder.objects.count(), 0)

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
        with open(os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'invalidsample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('homework', response.data)
        self.assertIn('Unresolved `course`', str(response.data['homework']))
        self.assertEqual(ExternalCalendar.objects.count(), 0)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(CourseSchedule.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MaterialGroup.objects.count(), 0)
        self.assertEqual(Material.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Reminder.objects.count(), 0)

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
        material_group1 = materialgrouphelper.given_material_group_exists(user1)
        material_group2 = materialgrouphelper.given_material_group_exists(user2)
        material1 = materialhelper.given_material_exists(material_group1)
        materialhelper.given_material_exists(material_group2)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade="20/30", materials=[material1])
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
        export_response = self.client.get(reverse('importexport_export'))
        self.assertEqual(export_response.status_code, status.HTTP_200_OK)
        export_data = json.loads(export_response.content.decode('utf-8'))

        # THEN: export preserves both fields
        self.assertEqual(len(export_data['events']), 1)
        self.assertEqual(export_data['events'][0]['recurrence_rule'], 'FREQ=WEEKLY;BYDAY=MO,WE,FR')
        self.assertEqual(
            export_data['events'][0]['exception_dates'],
            ['2017-05-15T12:00:00Z', '2017-05-22T12:00:00Z'],
        )

        # WHEN: re-import the same payload as the same user
        upload_path = os.path.join(os.path.dirname(__file__), '..', '..', 'resources', '_rrule_roundtrip.json')
        try:
            with open(upload_path, 'w') as fp:
                json.dump(export_data, fp)
            with open(upload_path) as fp:
                import_response = self.client.post(reverse('importexport_import'), {'file[]': [fp]})
        finally:
            if os.path.exists(upload_path):
                os.remove(upload_path)

        # THEN: round-trip preserves both fields on the freshly-imported Event
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

    def test_user_registration_imports_example_schedule(self):
        # WHEN
        response = self.client.post(reverse('auth_user_resource_register'),
                                    json.dumps({'email': 'test@test.com', 'username': 'my_test_user',
                                                'password': 'test_pass_1!',
                                                'time_zone': 'America/Chicago'}),
                                    content_type='application/json')

        # GIVEN: compute anchor relative to user's local timezone (matches _adjust_schedule_relative_to)
        user_tz = ZoneInfo('America/Chicago')
        now = timezone.now().astimezone(user_tz)
        adjusted_month = now.month - 1
        adjusted_year = now.year
        if adjusted_month == 0:
            adjusted_month = 12
            adjusted_year -= 1

        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0,
                                     second=0, microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        start_of_month = adjusted_month.replace(day=first_monday.day, hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(Category.objects.count(), 15)
        self.assertEqual(MaterialGroup.objects.count(), 3)
        self.assertEqual(Material.objects.count(), 5)
        self.assertEqual(Homework.objects.count(), 53)
        self.assertEqual(Reminder.objects.count(), 16)
        self.assertEqual(Event.objects.count(), 9)

        homework1 = Homework.objects.all()[0]
        self.assertEqual(CourseGroup.objects.all()[0].start_date, start_of_month.date())
        self.assertEqual(Course.objects.all()[0].start_date, start_of_month.date())
        self.assertEqual(homework1.start.date(), homework1.course.start_date + datetime.timedelta(
            days=(homework1.start.date() - homework1.course.start_date).days))
        reminder = Reminder.objects.filter(event__isnull=False).first()
        self.assertEqual(reminder.start_of_range.date(), reminder.event.start.date())

        fourth_friday = first_monday + relativedelta(days=4, weeks=3)
        event = Event.objects.all()[4]
        self.assertEqual(event.start.date(), fourth_friday.date())
        self.assertEqual(event.end.date(), fourth_friday.date() + relativedelta(days=3))

        course_group = CourseGroup.objects.all()[0]
        course = Course.objects.for_course_group(course_group.pk)[1]
        category1 = Category.objects.for_course(course.pk)[2]
        category2 = Category.objects.for_course(course.pk)[4]
        self.assertEqual(float(course_group.overall_grade), 87.7934)
        self.assertEqual(float(course_group.trend), 0.0010061923076923659)
        self.assertEqual(float(course.current_grade), 89.0833)
        self.assertEqual(float(course.trend), 0.006485167832167846)
        self.assertEqual(float(category1.average_grade), 110)
        self.assertEqual(float(category1.grade_by_weight), 16.5)
        self.assertIsNone(category1.trend)
        self.assertEqual(float(category2.average_grade), 87.6)
        self.assertEqual(float(category2.grade_by_weight), 17.52)
        self.assertEqual(float(category2.trend), 0.011699999999999875)

        # 1 standalone + 27 direct links + 2 legacy = 30
        self.assertEqual(Note.objects.count(), 30)

        # 1 welcome + 8 events + 15 homework = 24 (materials have blank titles)
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        homework_with_notes = Homework.objects.filter(notes_set__isnull=False).distinct()
        self.assertGreater(homework_with_notes.count(), 0)

    def test_import_exampleschedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(reverse('importexport_import_exampleschedule'))

        # GIVEN: compute anchor relative to user's local timezone (matches _adjust_schedule_relative_to)
        user_tz = ZoneInfo('America/Los_Angeles')
        now = timezone.now().astimezone(user_tz)
        adjusted_month = now.month - 1
        adjusted_year = now.year
        if adjusted_month == 0:
            adjusted_month = 12
            adjusted_year -= 1

        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0, second=0,
                                     microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)
        first_monday_date = first_monday.date()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # --- Entity counts ---
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(Category.objects.count(), 15)
        self.assertEqual(MaterialGroup.objects.count(), 3)
        self.assertEqual(Material.objects.count(), 5)
        self.assertEqual(Homework.objects.count(), 53)
        self.assertEqual(Event.objects.count(), 9)
        # 15 from fixture + 1 created by create_next_repeating_reminder for the course reminder
        self.assertEqual(Reminder.objects.count(), 16)
        # 28 direct notes + 1 legacy homework comment + 1 legacy material details = 30
        self.assertEqual(Note.objects.count(), 30)

        # --- CourseGroup ---
        course_group = CourseGroup.objects.first()
        self.assertEqual(course_group.title, 'Fall Semester')
        self.assertEqual(course_group.start_date, first_monday_date)
        self.assertTrue(course_group.shown_on_calendar)
        self.assertEqual(float(course_group.overall_grade), 87.7934)
        self.assertAlmostEqual(course_group.trend, 0.0010061923076923659)
        self.assertTrue(course_group.example_schedule)
        self.assertEqual(course_group.user, user)

        # --- Courses (ordered by start_date, title) ---
        courses = list(Course.objects.all())
        self.assertEqual(len(courses), 3)

        course_titles = {c.title for c in courses}
        self.assertEqual(course_titles, {'Creative Writing ✍️', 'Fundamentals of Programming 💻', 'Intro to Psychology 🧠'})

        creative_writing = Course.objects.get(title='Creative Writing ✍️')
        self.assertEqual(creative_writing.room, 'ARTS 302')
        self.assertEqual(float(creative_writing.credits), 3.0)
        self.assertEqual(creative_writing.color, '#bd42a4')
        self.assertFalse(creative_writing.is_online)
        self.assertEqual(float(creative_writing.current_grade), 89.3269)
        self.assertAlmostEqual(creative_writing.trend, -0.0023276428571428922)
        self.assertEqual(creative_writing.teacher_name, 'Dr. Joey Rubik')
        self.assertEqual(creative_writing.teacher_email, 'joey.rubik@university.edu')
        self.assertEqual(creative_writing.start_date, first_monday_date)
        self.assertEqual(creative_writing.course_group, course_group)

        programming = Course.objects.get(title='Fundamentals of Programming 💻')
        self.assertEqual(programming.room, '')
        self.assertEqual(float(programming.credits), 3.0)
        self.assertEqual(programming.color, '#05cc90')
        self.assertEqual(programming.website, 'https://automatetheboringstuff.com')
        self.assertTrue(programming.is_online)
        self.assertEqual(float(programming.current_grade), 89.0833)
        self.assertAlmostEqual(programming.trend, 0.006485167832167846)
        self.assertEqual(programming.teacher_name, 'Dr. Alex Gallagher')
        self.assertEqual(programming.teacher_email, 'alex.gallagher@university.edu')
        self.assertEqual(programming.start_date, first_monday_date)

        psychology = Course.objects.get(title='Intro to Psychology 🧠')
        self.assertEqual(psychology.room, 'SOC 110')
        self.assertEqual(float(psychology.credits), 4.0)
        self.assertEqual(psychology.color, '#3033cf')
        self.assertFalse(psychology.is_online)
        self.assertEqual(float(psychology.current_grade), 84.97)
        self.assertAlmostEqual(psychology.trend, 0.01880931428571422)
        self.assertEqual(psychology.teacher_name, 'Dr. Jess Otter')
        self.assertEqual(psychology.teacher_email, 'jess.otter@university.edu')

        # --- CourseSchedules ---
        cw_schedule = CourseSchedule.objects.get(course=creative_writing)
        self.assertEqual(cw_schedule.days_of_week, '0010100')
        self.assertEqual(cw_schedule.tue_start_time, datetime.time(11, 0))
        self.assertEqual(cw_schedule.tue_end_time, datetime.time(11, 50))
        self.assertEqual(cw_schedule.thu_start_time, datetime.time(11, 0))
        self.assertEqual(cw_schedule.thu_end_time, datetime.time(11, 50))

        prog_schedule = CourseSchedule.objects.get(course=programming)
        self.assertEqual(prog_schedule.days_of_week, '0101010')
        self.assertEqual(prog_schedule.mon_start_time, datetime.time(11, 0))
        self.assertEqual(prog_schedule.mon_end_time, datetime.time(11, 50))

        psych_schedule = CourseSchedule.objects.get(course=psychology)
        self.assertEqual(psych_schedule.days_of_week, '0101010')
        self.assertEqual(psych_schedule.mon_start_time, datetime.time(13, 0))
        self.assertEqual(psych_schedule.mon_end_time, datetime.time(13, 50))

        # --- Categories (4 + 5 + 6 = 15) ---
        cw_categories = Category.objects.filter(course=creative_writing).order_by('title')
        self.assertEqual(cw_categories.count(), 4)
        cw_cat_titles = list(cw_categories.values_list('title', flat=True))
        self.assertEqual(cw_cat_titles, ['Essay 📝', 'Final Portfolio 📚', 'Reading 📖', 'Short Stories 🪶'])

        essay_cat = cw_categories.get(title='Essay 📝')
        self.assertEqual(float(essay_cat.weight), 40.0)
        self.assertEqual(essay_cat.color, '#c964b5')
        self.assertEqual(float(essay_cat.average_grade), 88.6)
        self.assertEqual(float(essay_cat.grade_by_weight), 35.44)
        self.assertAlmostEqual(essay_cat.trend, -0.022299999999999975)

        reading_cat = cw_categories.get(title='Reading 📖')
        self.assertEqual(float(reading_cat.weight), 0.0)
        self.assertEqual(float(reading_cat.average_grade), -1.0)
        self.assertEqual(float(reading_cat.grade_by_weight), 0.0)

        prog_categories = Category.objects.filter(course=programming).order_by('title')
        self.assertEqual(prog_categories.count(), 5)
        prog_cat_titles = list(prog_categories.values_list('title', flat=True))
        self.assertEqual(prog_cat_titles, ['Final Exam 📈', 'Homework 👨🏽‍💻', 'Midterm 📊', 'Project 🔨', 'Quiz 💡'])

        midterm_cat = prog_categories.get(title='Midterm 📊')
        self.assertEqual(float(midterm_cat.weight), 15.0)
        self.assertEqual(float(midterm_cat.average_grade), 110.0)
        self.assertEqual(float(midterm_cat.grade_by_weight), 16.5)
        self.assertIsNone(midterm_cat.trend)

        quiz_cat = prog_categories.get(title='Quiz 💡')
        self.assertEqual(float(quiz_cat.weight), 20.0)
        self.assertEqual(float(quiz_cat.average_grade), 87.6)
        self.assertEqual(float(quiz_cat.grade_by_weight), 17.52)
        self.assertAlmostEqual(quiz_cat.trend, 0.011699999999999875)

        psych_categories = Category.objects.filter(course=psychology).order_by('title')
        self.assertEqual(psych_categories.count(), 6)
        psych_cat_titles = list(psych_categories.values_list('title', flat=True))
        self.assertEqual(psych_cat_titles, ['Capstone Case Study 🧩', 'Case Study 🔎', 'Final Exam 📈', 'Midterm 📊',
                                            'Quiz 💡', 'Reading 📖'])

        # Verify cumulative weights per course don't exceed 100
        for course in courses:
            total_weight = sum(float(c.weight) for c in Category.objects.filter(course=course))
            self.assertLessEqual(total_weight, 100.0)

        # --- MaterialGroups ---
        material_groups = MaterialGroup.objects.all().order_by('title')
        self.assertEqual(material_groups.count(), 3)
        mg_titles = list(material_groups.values_list('title', flat=True))
        self.assertEqual(mg_titles, ['Digital Tools', 'Supplies', 'Textbooks'])
        for mg in material_groups:
            self.assertTrue(mg.shown_on_calendar)
            self.assertTrue(mg.example_schedule)
            self.assertEqual(mg.user, user)

        # --- Materials ---
        materials = Material.objects.all().order_by('title')
        self.assertEqual(materials.count(), 5)

        automate = materials.get(title='Automate the Boring Stuff with Python')
        self.assertEqual(automate.price, '$28.99')
        self.assertEqual(automate.material_group, material_groups.get(title='Textbooks'))
        self.assertEqual(list(automate.courses.values_list('title', flat=True)), ['Fundamentals of Programming 💻'])

        google = materials.get(title='Google Workspace (Docs, Drive)')
        self.assertEqual(google.price, 'Free')
        self.assertEqual(google.status, 7)
        self.assertEqual(google.condition, 8)
        self.assertEqual(google.material_group, material_groups.get(title='Digital Tools'))
        self.assertEqual(google.courses.count(), 3)

        notebook = materials.get(title='Notebook 📓')
        self.assertEqual(notebook.price, '$5.00')
        self.assertEqual(notebook.material_group, material_groups.get(title='Supplies'))
        self.assertEqual(notebook.courses.count(), 2)
        self.assertFalse(notebook.courses.filter(title='Fundamentals of Programming 💻').exists())

        bird = materials.get(title='Bird by Bird: Some Instructions on Writing and Life')
        self.assertEqual(bird.price, '$16.00')
        self.assertEqual(bird.status, 1)
        self.assertEqual(list(bird.courses.values_list('title', flat=True)), ['Creative Writing ✍️'])

        psych_textbook = materials.get(title='Psychology, 14th Edition')
        self.assertEqual(psych_textbook.price, '$45.00')
        self.assertEqual(list(psych_textbook.courses.values_list('title', flat=True)), ['Intro to Psychology 🧠'])

        # --- Events ---
        events = Event.objects.all()
        self.assertEqual(events.count(), 9)

        event_titles = list(events.values_list('title', flat=True))
        self.assertIn('Writing Workshop', event_titles)
        self.assertIn('Group Meeting (Programming)', event_titles)
        self.assertIn('Parents Weekend', event_titles)
        self.assertIn('Study Session (Midterm, Programming)', event_titles)
        self.assertIn('Study Session (Final, Psych)', event_titles)
        self.assertIn('Study Session (Final, Programming)', event_titles)
        self.assertIn('Final Portfolio Writing Workshop', event_titles)
        self.assertEqual(event_titles.count('Writing Workshop'), 3)

        parents_weekend = events.get(title='Parents Weekend')
        self.assertTrue(parents_weekend.all_day)
        self.assertEqual(parents_weekend.priority, 50)
        self.assertTrue(parents_weekend.example_schedule)
        self.assertEqual(parents_weekend.user, user)

        study_midterm = events.get(title='Study Session (Midterm, Programming)')
        self.assertFalse(study_midterm.all_day)
        self.assertTrue(study_midterm.show_end_time)
        self.assertEqual(study_midterm.priority, 60)
        self.assertIsNone(study_midterm.url)
        self.assertIsNone(study_midterm.owner_id)
        self.assertEqual(study_midterm.user, user)

        for event in events:
            self.assertTrue(event.example_schedule)
            self.assertEqual(event.user, user)

        # --- Homework ---
        all_homework = Homework.objects.all()
        self.assertEqual(all_homework.count(), 53)
        self.assertEqual(all_homework.filter(completed=True).count(), 35)
        self.assertEqual(all_homework.filter(completed=False).count(), 18)

        graded_hw = [h for h in all_homework if h.current_grade and '/' in h.current_grade
                     and not h.current_grade.startswith('-1/')]
        self.assertEqual(len(graded_hw), 25)

        # Verify every homework belongs to one of the imported courses and has a category
        for hw in all_homework:
            self.assertIn(hw.course, courses)
            self.assertIsNotNone(hw.category)

        # Verify homework-material M2M relationships
        hw_with_materials = all_homework.filter(materials__isnull=False).distinct()
        self.assertEqual(hw_with_materials.count(), 53)

        # Verify completed homework has completed_at set
        for hw in all_homework.filter(completed=True):
            self.assertIsNotNone(hw.completed_at)

        # Spot-check specific homework
        essay1_list = list(Homework.objects.filter(title='Essay 1'))
        self.assertEqual(len(essay1_list), 1)
        essay1 = essay1_list[0]
        self.assertFalse(essay1.all_day)
        self.assertFalse(essay1.show_end_time)
        self.assertEqual(essay1.priority, 46)
        self.assertIsNone(essay1.url)
        self.assertEqual(essay1.current_grade, '95/100')
        self.assertTrue(essay1.completed)
        self.assertIsNotNone(essay1.completed_at)
        self.assertEqual(essay1.course, creative_writing)
        self.assertEqual(essay1.category, essay_cat)
        self.assertEqual(essay1.materials.count(), 2)
        self.assertTrue(essay1.materials.filter(title='Google Workspace (Docs, Drive)').exists())
        self.assertTrue(essay1.materials.filter(title='Notebook 📓').exists())
        # Legacy comments field should be converted to a Note
        self.assertTrue(essay1.notes_set.exists())
        legacy_note = essay1.notes_set.filter(title='').first()
        self.assertIsNotNone(legacy_note)
        self.assertIn('ops', legacy_note.content)

        midterm_prog = Homework.objects.get(title='Midterm', course=programming)
        self.assertEqual(midterm_prog.current_grade, '55/50')
        self.assertTrue(midterm_prog.completed)
        self.assertEqual(midterm_prog.category, midterm_cat)

        # Verify date adjustment: all homework dates are relative to first_monday
        for hw in all_homework.select_related('course'):
            self.assertGreaterEqual(hw.start.date(), hw.course.start_date)

        # --- Reminders ---
        all_reminders = Reminder.objects.all()
        self.assertEqual(all_reminders.count(), 16)

        hw_reminders = all_reminders.filter(homework__isnull=False)
        event_reminders = all_reminders.filter(event__isnull=False)
        course_reminders = all_reminders.filter(course__isnull=False)
        self.assertEqual(hw_reminders.count(), 12)
        self.assertEqual(event_reminders.count(), 2)
        self.assertGreaterEqual(course_reminders.count(), 1)

        # Verify every reminder belongs to the user and has exactly one parent
        for reminder in all_reminders:
            self.assertEqual(reminder.user, user)
            parents = sum([
                reminder.homework_id is not None,
                reminder.event_id is not None,
                reminder.course_id is not None,
            ])
            self.assertEqual(parents, 1)

        # Event reminders: two types (0 and 3) for the same event
        for reminder in event_reminders:
            self.assertEqual(reminder.event, study_midterm)
            self.assertEqual(reminder.title, 'Bring notes for group')
            self.assertEqual(reminder.message, 'Bring notes for group')
            self.assertEqual(reminder.offset, 30)
            self.assertEqual(reminder.offset_type, 0)
            self.assertTrue(reminder.sent)
            self.assertFalse(reminder.dismissed)
        event_reminder_types = set(event_reminders.values_list('type', flat=True))
        self.assertEqual(event_reminder_types, {0, 3})

        # Course reminder should reference Creative Writing
        course_reminder = course_reminders.filter(sent=True).first()
        self.assertIsNotNone(course_reminder)
        self.assertEqual(course_reminder.course, creative_writing)
        self.assertEqual(course_reminder.title, 'Class starts soon')
        self.assertEqual(course_reminder.message, 'Class starts soon')
        self.assertEqual(course_reminder.offset, 10)
        self.assertEqual(course_reminder.offset_type, 0)
        self.assertEqual(course_reminder.type, 3)
        self.assertTrue(course_reminder.sent)

        # Homework reminders: verify start_of_range is computed relative to the homework start
        for reminder in hw_reminders:
            self.assertIsNotNone(reminder.start_of_range)

        # --- Notes ---
        all_notes = Note.objects.all()
        self.assertEqual(all_notes.count(), 30)

        # Standalone notes (no entity links)
        standalone_notes = Note.objects.filter(
            homework__isnull=True
        ).filter(
            events__isnull=True
        ).filter(
            resources__isnull=True
        )
        self.assertEqual(standalone_notes.count(), 1)
        welcome_note = standalone_notes.first()
        self.assertEqual(welcome_note.title, 'A Study Session Template')
        self.assertIn('ops', welcome_note.content)
        self.assertTrue(welcome_note.example_schedule)
        self.assertEqual(welcome_note.user, user)

        # Titled notes: 1 welcome + 8 events + 15 homework = 24
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        # Untitled notes: 5 material links + 1 legacy homework comment = 6
        untitled_notes = Note.objects.filter(title='')
        self.assertEqual(untitled_notes.count(), 6)

        # Notes linked to homework
        hw_notes = Note.objects.filter(homework__isnull=False).distinct()
        self.assertEqual(hw_notes.count(), 16)

        # Notes linked to events
        event_notes = Note.objects.filter(events__isnull=False).distinct()
        self.assertEqual(event_notes.count(), 8)

        sprint_note = Note.objects.filter(title='Sprint Planning').first()
        self.assertIsNotNone(sprint_note)
        self.assertTrue(sprint_note.events.exists())
        self.assertIn('ops', sprint_note.content)

        # Notes linked to materials (resources)
        material_notes = Note.objects.filter(resources__isnull=False).distinct()
        self.assertEqual(material_notes.count(), 5)
        for note in material_notes:
            self.assertIn('ops', note.content)

        # Legacy notes: material 'Notebook' has legacy details
        notebook_legacy_notes = notebook.notes_set.filter(title='')
        self.assertEqual(notebook_legacy_notes.count(), 1)
        notebook_note = notebook_legacy_notes.first()
        self.assertIn('ops', notebook_note.content)

        # All notes should be marked as example_schedule and belong to user
        for note in all_notes:
            self.assertTrue(note.example_schedule)
            self.assertEqual(note.user, user)

        # --- User settings ---
        user.settings.refresh_from_db()
        self.assertTrue(user.settings.show_getting_started)

    def test_import_legacy_notes_converted_to_quill(self):
        """Test that importing legacy HTML comments/details converts them to Quill JSON notes."""
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # Import data with legacy HTML formatting
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
                'title': 'Uncategorized',
                'weight': '0.00',
                'average_grade': '-1',
                'grade_by_weight': '0',
                'color': '#4986e7',
                'course': 1
            }],
            'material_groups': [{
                'id': 1,
                'title': 'Test Materials',
                'shown_on_calendar': True,
                'user': 1
            }],
            'materials': [{
                'id': 1,
                'title': 'Test Book',
                'status': 0,
                'condition': 0,
                'website': '',
                'price': '',
                'details': '<b>ISBN:</b> 978-1234567890',  # Legacy HTML
                'material_group': 1,
                'courses': []
            }],
            'events': [{
                'id': 1,
                'title': 'Test Event',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-01T10:00:00Z',
                'end': '2024-02-01T11:00:00Z',
                'priority': 50,
                'url': None,
                'comments': '<ul><li>Item 1</li><li>Item 2</li></ul>',  # Legacy HTML list
                'user': 1
            }],
            'homework': [{
                'id': 1,
                'title': 'Test Assignment',
                'all_day': False,
                'show_end_time': True,
                'start': '2024-02-01T10:00:00Z',
                'end': '2024-02-01T12:00:00Z',
                'priority': 50,
                'url': None,
                'comments': '<p>Due by <strong>midnight</strong></p>',  # Legacy HTML with formatting
                'current_grade': '-1/100',
                'completed': False,
                'category': 1,
                'materials': [],
                'course': 1
            }],
            'reminders': [],
            'course_schedules': []
        }

        # WHEN
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(import_data, f)
            f.flush()
            with open(f.name, 'rb') as fp:
                response = self.client.post(reverse('importexport_import'), {'file[]': [fp]})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Legacy fields should be preserved (not cleared) for backward compatibility
        material = Material.objects.first()
        self.assertEqual(material.details, '<b>ISBN:</b> 978-1234567890')
        self.assertTrue(material.notes_set.exists())
        material_note = material.notes_set.first()
        self.assertIn('ops', material_note.content)
        bold_op = next((op for op in material_note.content['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'ISBN:')

        event = Event.objects.first()
        self.assertEqual(event.comments, '<ul><li>Item 1</li><li>Item 2</li></ul>')
        self.assertTrue(event.notes_set.exists())
        event_note = event.notes_set.first()
        self.assertIn('ops', event_note.content)
        list_op = next((op for op in event_note.content['ops'] if op.get('attributes', {}).get('list')), None)
        self.assertIsNotNone(list_op)
        self.assertEqual(list_op['attributes']['list'], 'bullet')

        homework = Homework.objects.first()
        self.assertEqual(homework.comments, '<p>Due by <strong>midnight</strong></p>')
        self.assertTrue(homework.notes_set.exists())
        homework_note = homework.notes_set.first()
        self.assertIn('ops', homework_note.content)
        bold_op = next((op for op in homework_note.content['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'midnight')

        self.assertEqual(Note.objects.filter(user=user).count(), 3)

    def test_import_notes_with_direct_entity_links(self):
        """Test importing notes with direct M2M links to entities (new format)."""
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
            'material_groups': [{
                'id': 1,
                'title': 'Test Materials',
                'shown_on_calendar': True,
                'user': 1
            }],
            'materials': [{
                'id': 100,
                'title': 'Test Textbook',
                'status': 0,
                'condition': 0,
                'website': '',
                'price': '$50.00',
                'material_group': 1,
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
                'url': None,
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
                'materials': [100],
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
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(import_data, f)
            f.flush()
            with open(f.name, 'rb') as fp:
                response = self.client.post(reverse('importexport_import'), {'file[]': [fp]})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Note.objects.count(), 4)

        material = Material.objects.first()
        textbook_note = Note.objects.get(title='Textbook ISBN')
        self.assertTrue(textbook_note.resources.filter(pk=material.pk).exists())

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
            'material_groups': [{
                'id': 1, 'title': 'MG', 'shown_on_calendar': True, 'user': 1,
            }],
            'materials': [{
                'id': 1, 'title': 'M', 'status': 0, 'condition': 0, 'website': '',
                'price': '', 'material_group': 1, 'courses': [],
            }],
            'events': [],
            'homework': [],
            'reminders': [],
            'notes': [],
            'course_schedules': [],
        }

    def _post_import(self, payload):
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(payload, f)
            f.flush()
            with open(f.name, 'rb') as fp:
                return self.client.post(reverse('importexport_import'), {'file[]': [fp]})

    def test_import_note_invalid_payload_rejects_whole_import(self):
        # GIVEN: a note linked to both a homework AND an event (mutually exclusive)
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['events'] = [{
            'id': 10, 'title': 'E', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T11:00:00Z', 'priority': 50,
        }]
        payload['homework'] = [{
            'id': 20, 'title': 'H', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T12:00:00Z', 'priority': 50,
            'current_grade': '-1/100', 'completed': False, 'category': 1, 'materials': [],
            'course': 1,
        }]
        payload['notes'] = [{
            'id': 1, 'title': 'Bad', 'content': {'ops': [{'insert': 'x\n'}]},
            'homework': [20], 'events': [10], 'resources': [],
        }]

        # WHEN
        response = self._post_import(payload)

        # THEN: 400 and nothing landed (atomic rollback)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Note.objects.count(), 0)

    def test_import_unresolved_course_group_returns_400_not_500(self):
        # GIVEN: a course referencing a course_group id that doesn't appear in the file
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'][0]['course_group'] = 999  # not in the file

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('Unresolved `course_group`', str(response.data['courses']))
        self.assertEqual(Course.objects.count(), 0)

    def test_import_unresolved_course_on_category_returns_400_not_500(self):
        # GIVEN: a category referencing a course id that doesn't appear in the file
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['categories'][0]['course'] = 999

        # WHEN
        response = self._post_import(payload)

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
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('course_schedules', response.data)
        self.assertIn('Unresolved `course`', str(response.data['course_schedules']))

    def test_import_duplicate_id_within_section_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'].append({**payload['courses'][0], 'title': 'C2'})

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('Duplicate id', str(response.data['courses']))

    def test_import_non_integer_id_rejected(self):
        # GIVEN: an id that is neither an int nor a coercible string-int
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['courses'][0]['id'] = {'oops': 'not-an-id'}

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('not a valid id', str(response.data['courses']))

    def test_import_string_int_id_coerced(self):
        # GIVEN: ids supplied as strings should be coerced
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['course_groups'][0]['id'] = '1'
        payload['courses'][0]['id'] = '1'
        payload['courses'][0]['course_group'] = '1'

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Course.objects.count(), 1)

    def test_import_missing_id_in_section_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        del payload['courses'][0]['id']

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('courses', response.data)
        self.assertIn('missing required key `id`', str(response.data['courses']))

    def test_import_both_resources_and_materials_top_level_rejected(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['resources'] = list(payload['materials'])

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Provide either 'resources' or 'materials'", str(response.data))
        self.assertEqual(Material.objects.count(), 0)

    def test_import_top_level_resources_alias_succeeds(self):
        # GIVEN: top-level `resources` instead of `materials`
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['resources'] = payload.pop('materials')

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Material.objects.count(), 1)

    def test_import_top_level_materials_alias_succeeds(self):
        # GIVEN: top-level `materials` alias (export shape)
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Material.objects.count(), 1)

    def test_import_note_both_resources_and_materials_rejected(self):
        # GIVEN: a Note with both `resources` and `materials` keys
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['notes'] = [{
            'id': 1, 'title': 'Bad', 'content': {'ops': [{'insert': 'x\n'}]},
            'resources': [1], 'materials': [1],
        }]

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Provide either 'resources' or 'materials'", str(response.data))
        self.assertEqual(Note.objects.count(), 0)

    def test_import_note_materials_alias_succeeds(self):
        # GIVEN: a Note using `materials` alias
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['notes'] = [{
            'id': 1, 'title': 'Alias', 'content': {'ops': [{'insert': 'x\n'}]},
            'materials': [1],
        }]

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note = Note.objects.get(title='Alias')
        self.assertEqual(note.resources.count(), 1)

    def test_import_homework_unresolved_material_returns_400(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        payload = self._minimal_import_payload()
        payload['homework'] = [{
            'id': 10, 'title': 'H', 'all_day': False, 'show_end_time': False,
            'start': '2024-02-01T10:00:00Z', 'end': '2024-02-01T12:00:00Z', 'priority': 50,
            'current_grade': '-1/100', 'completed': False, 'category': 1,
            'materials': [9999],  # not in payload
            'course': 1,
        }]

        # WHEN
        response = self._post_import(payload)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('homework', response.data)
        self.assertIn('Unresolved `materials`', str(response.data['homework']))
