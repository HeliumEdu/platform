__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json
import logging
import os

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

logger = logging.getLogger(__name__)


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

    def test_import_success(self):
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
             'material_groups': 1, 'materials': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 0}, response1.data)
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
             'material_groups': 1, 'materials': 1, 'events': 2, 'homework': 2, 'reminders': 2, 'notes': 0}, response2.data)
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
                                                                     'color': '#fad165', 'shown_on_calendar': False,
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
        # Legacy 'details' field is converted to 'notes' on import
        materialhelper.verify_material_matches_data(self, materials[1],
                                                    {'title': '📘 Test Material', 'status': 3, 'condition': 7,
                                                     'website': 'http://www.material.com', 'price': '9.99',
                                                     'details': '',  # Legacy field is not populated on import
                                                     'material_group': material_groups[1].pk, 'courses': []})
        # Verify legacy 'details' was converted to 'notes' Quill JSON
        self.assertIsNotNone(materials[1].notes)
        self.assertIn('ops', materials[1].notes)
        self.assertEqual(materials[1].notes['ops'][0]['insert'], 'Return by 7/1')
        # Verify Note was created for material
        self.assertTrue(materials[1].notes_set.exists())
        self.assertEqual(materials[1].notes_set.first().content, materials[1].notes)

        # Legacy 'comments' field is converted to 'notes' on import
        eventhelper.verify_event_matches_data(self, events[2],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': '',  # Legacy field not populated
                                               'owner_id': None, 'user': user.pk})
        eventhelper.verify_event_matches_data(self, events[3],
                                              {'title': '🏀 Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': '',  # Legacy field not populated
                                               'owner_id': None, 'user': user.pk})
        # Verify legacy 'comments' was converted to 'notes' Quill JSON for events
        self.assertIsNotNone(events[2].notes)
        self.assertIn('ops', events[2].notes)
        self.assertEqual(events[2].notes['ops'][0]['insert'], 'A comment on an event.')
        # Verify Note was created for event
        self.assertTrue(events[2].notes_set.exists())
        self.assertEqual(events[2].notes_set.first().content, events[2].notes)

        # Legacy 'comments' field is converted to 'notes' on import
        homeworkhelper.verify_homework_matches_data(self, homework[2],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': '',  # Legacy field not populated
                                                     'current_grade': '20/30',
                                                     'completed': True, 'category': categories[1].pk,
                                                     'course': courses[2].pk, 'materials': [materials[1].pk]})
        homeworkhelper.verify_homework_matches_data(self, homework[3],
                                                    {'title': '💻 Test Homework', 'all_day': False,
                                                     'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': '',  # Legacy field not populated
                                                     'current_grade': '-1/100',
                                                     'completed': False, 'category': categories[3].pk,
                                                     'course': courses[3].pk, 'materials': []})
        # Verify legacy 'comments' was converted to 'notes' Quill JSON for homework
        self.assertIsNotNone(homework[2].notes)
        self.assertIn('ops', homework[2].notes)
        self.assertEqual(homework[2].notes['ops'][0]['insert'], 'A comment on a homework.')
        # Verify Note was created for homework
        self.assertTrue(homework[2].notes_set.exists())
        self.assertEqual(homework[2].notes_set.first().content, homework[2].notes)

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
        self.assertIn('course', response.data['homework'][1])
        self.assertIn('may not be null', response.data['homework'][1]['course'][0])
        self.assertIn('materials', response.data['homework'][1])
        self.assertIn('object does not exist', response.data['homework'][1]['materials'][0])
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
        category2 = categoryhelper.given_category_exists(course2)
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

    def test_user_registration_imports_example_schedule(self):
        # WHEN
        response = self.client.post(reverse('auth_user_resource_register'),
                                    json.dumps({'email': 'test@test.com', 'username': 'my_test_user',
                                                'password': 'test_pass_1!',
                                                'time_zone': 'America/Chicago'}),
                                    content_type='application/json')

        # GIVEN
        now = timezone.now()
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
        self.assertEqual(Reminder.objects.count(), 14)
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

        # Verify Notes were imported (1 standalone + 27 direct links + 2 legacy = 30)
        self.assertEqual(Note.objects.count(), 30)

        # Verify notes with titles were linked correctly
        # 1 welcome + 8 events + 15 homework = 24 (materials have blank titles)
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        # Verify entity.notes fields were populated for linked notes
        homework_with_notes = Homework.objects.exclude(notes__isnull=True).exclude(notes={})
        self.assertGreater(homework_with_notes.count(), 0)
        for hw in homework_with_notes:
            self.assertTrue(hw.notes_set.exists())

    def test_import_exampleschedule(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.post(reverse('importexport_import_exampleschedule'))

        now = timezone.now()
        adjusted_month = now.month - 1
        adjusted_year = now.year
        if adjusted_month == 0:
            adjusted_month = 12
            adjusted_year -= 1

        # GIVEN
        adjusted_month = now.replace(year=adjusted_year, month=adjusted_month, day=1, hour=0, minute=0, second=0,
                                     microsecond=0)
        days_ahead = 0 - adjusted_month.weekday()
        if days_ahead < 0:
            days_ahead += 7
        first_monday = adjusted_month + datetime.timedelta(days_ahead)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        adjusted_month.replace(day=first_monday.day, hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 3)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(Category.objects.count(), 15)
        self.assertEqual(MaterialGroup.objects.count(), 3)
        self.assertEqual(Material.objects.count(), 5)
        self.assertEqual(Homework.objects.count(), 53)
        self.assertEqual(Reminder.objects.count(), 14)
        self.assertEqual(Event.objects.count(), 9)

        # Verify Notes were imported correctly
        # Example schedule has: 1 standalone + 27 with direct links + 2 legacy conversions = 30 total
        self.assertEqual(Note.objects.count(), 30)

        # Verify standalone note (no entity links)
        standalone_notes = Note.objects.filter(
            homework__isnull=True
        ).filter(
            events__isnull=True
        ).filter(
            resources__isnull=True
        )
        self.assertEqual(standalone_notes.count(), 1)
        welcome_note = standalone_notes.first()
        self.assertEqual(welcome_note.title, 'Ace Your Classes - Welcome to Helium!')
        self.assertIn('ops', welcome_note.content)

        # Verify notes imported with direct entity links (new format)
        # These have titles and are linked to entities
        # 1 welcome + 8 events + 15 homework = 24 (materials have blank titles)
        titled_notes = Note.objects.exclude(title='')
        self.assertEqual(titled_notes.count(), 24)

        # Verify a specific titled note linked to homework
        sprint_note = Note.objects.filter(title='Sprint Planning').first()
        self.assertIsNotNone(sprint_note)
        self.assertTrue(sprint_note.events.exists())
        self.assertIn('ops', sprint_note.content)
        # Verify entity's notes field was synced
        linked_event = sprint_note.events.first()
        self.assertEqual(linked_event.notes, sprint_note.content)

        material_notes = Note.objects.filter(resources__isnull=False)
        self.assertEqual(material_notes.count(), 5)
        material_note = material_notes.first()
        self.assertIn('ops', material_note.content)
        linked_material = material_note.resources.first()
        self.assertEqual(linked_material.notes, material_note.content)

        untitled_notes = Note.objects.filter(title='')
        self.assertEqual(untitled_notes.count(), 6)

        # Verify homework's notes field and linked Note for legacy item
        hw_with_legacy = Homework.objects.filter(notes__isnull=False).exclude(notes={})
        self.assertGreater(hw_with_legacy.count(), 0)
        for hw in hw_with_legacy:
            self.assertTrue(hw.notes_set.exists())

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

        # Verify material's legacy 'details' was converted
        material = Material.objects.first()
        self.assertEqual(material.details, '')  # Legacy field should be empty
        self.assertIsNotNone(material.notes)
        self.assertIn('ops', material.notes)
        # Check bold formatting was preserved
        bold_op = next((op for op in material.notes['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'ISBN:')

        # Verify event's legacy 'comments' was converted (list structure)
        event = Event.objects.first()
        self.assertEqual(event.comments, '')  # Legacy field should be empty
        self.assertIsNotNone(event.notes)
        self.assertIn('ops', event.notes)
        # Check list formatting was preserved
        list_op = next((op for op in event.notes['ops'] if op.get('attributes', {}).get('list')), None)
        self.assertIsNotNone(list_op)
        self.assertEqual(list_op['attributes']['list'], 'bullet')

        # Verify homework's legacy 'comments' was converted (paragraph with bold)
        homework = Homework.objects.first()
        self.assertEqual(homework.comments, '')  # Legacy field should be empty
        self.assertIsNotNone(homework.notes)
        self.assertIn('ops', homework.notes)
        # Check bold formatting was preserved
        bold_op = next((op for op in homework.notes['ops'] if op.get('attributes', {}).get('bold')), None)
        self.assertIsNotNone(bold_op)
        self.assertEqual(bold_op['insert'], 'midnight')

        # Verify Note entries were created
        self.assertEqual(Note.objects.filter(user=user).count(), 3)
        self.assertTrue(material.notes_set.exists())
        self.assertTrue(event.notes_set.exists())
        self.assertTrue(homework.notes_set.exists())

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

        # Verify note linked to material (resource)
        material = Material.objects.first()
        textbook_note = Note.objects.get(title='Textbook ISBN')
        self.assertTrue(textbook_note.resources.filter(pk=material.pk).exists())
        self.assertEqual(material.notes, textbook_note.content)

        # Verify note linked to event
        event = Event.objects.first()
        study_note = Note.objects.get(title='Study Topics')
        self.assertTrue(study_note.events.filter(pk=event.pk).exists())
        self.assertEqual(event.notes, study_note.content)

        # Verify note linked to homework
        homework = Homework.objects.first()
        assignment_note = Note.objects.get(title='Assignment Notes')
        self.assertTrue(assignment_note.homework.filter(pk=homework.pk).exists())
        self.assertEqual(homework.notes, assignment_note.content)

        # Verify standalone note (no entity links)
        standalone_note = Note.objects.get(title='Standalone Note')
        self.assertFalse(standalone_note.homework.exists())
        self.assertFalse(standalone_note.events.exists())
        self.assertFalse(standalone_note.resources.exists())
