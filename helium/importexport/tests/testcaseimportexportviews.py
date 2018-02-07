import json
import logging
import os

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
            response = self.client.post(
                reverse('importexport_import'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.count(), 2)
        self.assertEqual(Course.objects.count(), 2)
        self.assertEqual(Category.objects.count(), 2)
        self.assertEqual(MaterialGroup.objects.count(), 1)
        self.assertEqual(Material.objects.count(), 1)
        self.assertEqual(Event.objects.count(), 2)
        self.assertEqual(Homework.objects.count(), 2)
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
        self.assertIn('course', response.data['homework'])
        self.assertIn('object does not exist', response.data['homework']['course'][0])
        self.assertIn('materials', response.data['homework'])
        self.assertIn('object does not exist', response.data['homework']['materials'][0])
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
        externalcalendarhelper.given_external_calendar_exists(user1)
        eventhelper.given_event_exists(user1)
        eventhelper.given_event_exists(user1)
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
        homeworkhelper.given_homework_exists(course2, category=category2, current_grade="-1/100")
        homeworkhelper.given_homework_exists(course3, category=category3, completed=True, current_grade="-1/100")
        reminderhelper.given_reminder_exists(user1, homework=homework1)

        # WHEN
        response = self.client.get(reverse('importexport_export'))
        json_str = open(os.path.join(os.path.dirname(__file__), os.path.join('resources', 'sample.json'))).read()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(json.loads(json_str), json.loads(response.content))
