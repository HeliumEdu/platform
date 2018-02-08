import json
import logging
import os

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.feed.models import ExternalCalendar
from helium.feed.tests.helpers import externalcalendarhelper
from helium.planner.models import CourseGroup, Course, Category, MaterialGroup, Material, Event, Homework, Reminder
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, materialgrouphelper, \
    materialhelper, eventhelper, homeworkhelper, attachmenthelper, reminderhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class TestCaseImportExportViews(TestCase):
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
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_import_success(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        with open(os.path.join(os.path.dirname(__file__), os.path.join('resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            self.client.post(
                reverse('importexport_import'),
                data)
        # We are intentionally uploading this file twice so that, in the case of unit tests, the key IDs do not line
        # up and the remapping is properly tested
        with open(os.path.join(os.path.dirname(__file__), os.path.join('resources', 'sample.json'))) as fp:
            data = {
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.count(), 4)
        self.assertEqual(Course.objects.count(), 4)
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(MaterialGroup.objects.count(), 2)
        self.assertEqual(Material.objects.count(), 2)
        self.assertEqual(Event.objects.count(), 4)
        self.assertEqual(Homework.objects.count(), 4)
        # TODO: implement more assertions

    def test_import_invalid_json(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)
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
        self.assertIn('detail', response.data)
        self.assertEqual(ExternalCalendar.objects.count(), 0)
        self.assertEqual(CourseGroup.objects.count(), 0)
        self.assertEqual(Course.objects.count(), 0)
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MaterialGroup.objects.count(), 0)
        self.assertEqual(Material.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Reminder.objects.count(), 0)

    def test_import_invalid_relationships(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        with open(os.path.join(os.path.dirname(__file__), os.path.join('resources', 'invalidsample.json'))) as fp:
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
        self.assertEqual(Category.objects.count(), 0)
        self.assertEqual(MaterialGroup.objects.count(), 0)
        self.assertEqual(Material.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertEqual(Reminder.objects.count(), 0)

    def test_export_success(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client)
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
        data = json.loads(response.content)

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
        categoryhelper.verify_category_matches_data(self, category1, data['categories'][1])
        categoryhelper.verify_category_matches_data(self, category2, data['categories'][0])
        homeworkhelper.verify_homework_matches_data(self, homework1, data['homework'][0])
        homeworkhelper.verify_homework_matches_data(self, homework2, data['homework'][1])
        reminderhelper.verify_reminder_matches_data(self, reminder, data['reminders'][0])

    def test_user_registration_imports_example_schedule(self):
        # GIVEN
        userhelper.verify_user_not_logged_in(self)

        # WHEN
        response = self.client.post(reverse('register'),
                                    {'email': 'test@test.com', 'username': 'my_test_user', 'password1': 'test_pass_1!',
                                     'password2': 'test_pass_1!', 'time_zone': 'America/Chicago'})

        # THEN
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(CourseGroup.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(Category.objects.count(), 11)
        self.assertEqual(MaterialGroup.objects.count(), 2)
        self.assertEqual(Material.objects.count(), 4)
        self.assertEqual(Homework.objects.count(), 22)
        # TODO: implement more assertions
