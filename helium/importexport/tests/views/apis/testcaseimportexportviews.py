__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.14"

import datetime
import json
import logging
import os

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import CourseGroup, Course, CourseSchedule, Category, MaterialGroup, Material, Event, \
    Homework, Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper, categoryhelper, \
    materialgrouphelper, materialhelper, eventhelper, homeworkhelper, attachmenthelper, reminderhelper

logger = logging.getLogger(__name__)


class TestCaseImportExportViews(APITestCase):
    def test_importexport_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('importexport_resource_import')),
            self.client.post(reverse('importexport_resource_export'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_import_success(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        with open(os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response1 = self.client.post(
                reverse('importexport_resource_import'),
                data)
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
        # We are intentionally uploading this file twice so that, in the case of unit tests, the key IDs do not line
        # up and the remapping is properly tested
        with open(os.path.join(os.path.dirname(__file__), os.path.join('../../resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response2 = self.client.post(
                reverse('importexport_resource_import'),
                data)

        # THEN
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
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
                                                                    {'id': 2, 'title': 'My Calendar',
                                                                     'url': 'http://go.com/valid-ical-feed',
                                                                     'color': '#fad165', 'shown_on_calendar': False,
                                                                     'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_groups[2], {'average_grade': 66.6667,
                                                                                    'start_date': '2017-01-06',
                                                                                    'end_date': '2017-05-08',
                                                                                    'private_slug': None,
                                                                                    'shown_on_calendar': True,
                                                                                    'title': 'Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_groups[3], {'average_grade': -1.0,
                                                                                    'start_date': '2017-01-06',
                                                                                    'end_date': '2017-05-08',
                                                                                    'private_slug': None,
                                                                                    'shown_on_calendar': True,
                                                                                    'title': 'Test Course Group',
                                                                                    'trend': None,
                                                                                    'user': user.pk})
        coursehelper.verify_course_matches_data(self, courses[2], {'title': 'Test Course', 'room': '',
                                                                   'credits': 5.0, 'color': '#4986e7',
                                                                   'website': 'http://mycourse.com', 'is_online': False,
                                                                   'current_grade': 66.6667, 'trend': None,
                                                                   'private_slug': None, 'teacher_name': 'My Teacher',
                                                                   'teacher_email': 'teacher@email.com',
                                                                   'start_date': '2017-01-06', 'end_date': '2017-05-08',
                                                                   'course_group': course_groups[2].pk})
        coursehelper.verify_course_matches_data(self, courses[3],
                                                {'title': 'Test Course', 'room': 'DNC 201', 'credits': 5.0,
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
        categoryhelper.verify_category_matches_data(self, categories[1],
                                                    {'title': 'Test Category 1', 'weight': 0.0, 'color': '#4986e7',
                                                     'average_grade': -1.0, 'grade_by_weight': 0.0, 'trend': None,
                                                     'course': courses[3].pk})
        categoryhelper.verify_category_matches_data(self, categories[3],
                                                    {'title': 'Uncategorized', 'weight': 0.0, 'color': '#4986e7',
                                                     'average_grade': 66.6667, 'grade_by_weight': 0.0, 'trend': None,
                                                     'course': courses[2].pk})
        materialgrouphelper.verify_material_group_matches_data(self, material_groups[1],
                                                               {'title': 'Test Material Group',
                                                                'shown_on_calendar': True, 'user': user.pk})
        materialhelper.verify_material_matches_data(self, materials[1],
                                                    {'title': 'Test Material', 'status': 3, 'condition': 7,
                                                     'website': 'http://www.material.com', 'price': '9.99',
                                                     'details': 'Return by 7/1',
                                                     'material_group': material_groups[1].pk, 'courses': []})
        eventhelper.verify_event_matches_data(self, events[2],
                                              {'title': 'Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': 'A comment on an event.',
                                               'owner_id': None, 'user': user.pk})
        eventhelper.verify_event_matches_data(self, events[3],
                                              {'title': 'Test Event', 'all_day': False, 'show_end_time': True,
                                               'start': '2017-05-08T12:00:00Z', 'end': '2017-05-08T14:00:00Z',
                                               'priority': 75, 'url': None, 'comments': 'A comment on an event.',
                                               'owner_id': None, 'user': user.pk})
        homeworkhelper.verify_homework_matches_data(self, homework[2],
                                                    {'title': 'Test Homework', 'all_day': False, 'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': 'A comment on a homework.', 'current_grade': '20/30',
                                                     'completed': True, 'category': categories[3].pk,
                                                     'course': courses[2].pk, 'materials': [materials[1].pk]})
        homeworkhelper.verify_homework_matches_data(self, homework[3],
                                                    {'title': 'Test Homework', 'all_day': False, 'show_end_time': True,
                                                     'start': '2017-05-08T16:00:00Z', 'end': '2017-05-08T18:00:00Z',
                                                     'priority': 65, 'url': None,
                                                     'comments': 'A comment on a homework.', 'current_grade': '-1/100',
                                                     'completed': False, 'category': categories[1].pk,
                                                     'course': courses[3].pk, 'materials': []})
        reminderhelper.verify_reminder_matches_data(self, reminders[2], {'id': 1, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45:00Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 2,
                                                                         'sent': False, 'homework': homework[0].pk,
                                                                         'event': None, 'user': user.pk})
        reminderhelper.verify_reminder_matches_data(self, reminders[3], {'id': 3, 'title': 'Test Homework Reminder',
                                                                         'message': 'You need to do something now.',
                                                                         'start_of_range': '2017-05-08T15:45Z',
                                                                         'offset': 15, 'offset_type': 0, 'type': 2,
                                                                         'sent': False, 'homework': homework[2].pk,
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
                reverse('importexport_resource_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)
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
                reverse('importexport_resource_import'),
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
        response = self.client.get(reverse('importexport_resource_export'))
        data = json.loads(response.content.decode('utf-8'))

        # THEN
        course_group1 = CourseGroup.objects.get(pk=course_group1.pk)
        course_group2 = CourseGroup.objects.get(pk=course_group2.pk)
        course1 = Course.objects.get(pk=course1.pk)
        course2 = Course.objects.get(pk=course2.pk)
        category1 = Category.objects.get(pk=category1.pk)
        category2 = Category.objects.get(pk=category2.pk)
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
        categoryhelper.verify_category_matches_data(self, category1, data['categories'][1])
        categoryhelper.verify_category_matches_data(self, category2, data['categories'][0])
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

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        start_of_current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(CourseSchedule.objects.count(), 2)
        self.assertEqual(Category.objects.count(), 11)
        self.assertEqual(MaterialGroup.objects.count(), 2)
        self.assertEqual(Material.objects.count(), 4)
        self.assertEqual(Homework.objects.count(), 22)
        self.assertEqual(Reminder.objects.count(), 5)
        self.assertEqual(Event.objects.count(), 3)

        homework1 = Homework.objects.all()[0]
        event = Event.objects.all()[0]
        start_of_event_month = event.start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reminder = Reminder.objects.all()[0]
        self.assertEqual(CourseGroup.objects.all()[0].start_date, start_of_current_month.date())
        self.assertEqual(Course.objects.all()[0].start_date, start_of_current_month.date())
        self.assertEqual(homework1.start.date(), homework1.course.start_date + datetime.timedelta(
            days=(homework1.start.date() - homework1.course.start_date).days))
        self.assertEqual(event.start.date(), start_of_event_month.date() + datetime.timedelta(
            days=(event.start.date() - start_of_event_month.date()).days))
        self.assertEqual(reminder.start_of_range.date(), reminder.homework.start.date())

        course_group = CourseGroup.objects.all()[0]
        course = Course.objects.for_course_group(course_group.pk)[0]
        category = Category.objects.for_course(course.pk)[2]
        self.assertEqual(float(course_group.average_grade), 86.2108)
        self.assertEqual(round(float(course_group.trend), 10), -0.0009202767)
        self.assertEqual(float(course.current_grade), 90.6358)
        self.assertEqual(round(float(course.trend), 10), 0.0039735045)
        self.assertEqual(float(category.average_grade), 91.5)
        self.assertEqual(float(category.grade_by_weight), 13.725)
        self.assertEqual(round(float(category.trend), 10), -0.0275)
