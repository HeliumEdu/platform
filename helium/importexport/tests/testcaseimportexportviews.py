import json
import logging
import os

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, materialgrouphelper, \
    materialhelper, eventhelper, homeworkhelper

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = "1.2.0"

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
        # TODO: implement assertions

    def test_import_invalid_json(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        # TODO: implement

        # THEN

    def test_import_invalid_relationships(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        # TODO: implement

        # THEN

    def test_export_success(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
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
        homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                             current_grade="20/30", materials=[material1])
        homeworkhelper.given_homework_exists(course2, category=category2, current_grade="-1/100")
        homeworkhelper.given_homework_exists(course3, category=category3, completed=True, current_grade="-1/100")

        # WHEN
        response = self.client.get(reverse('importexport_export'))
        json_str = open(os.path.join(os.path.dirname(__file__), os.path.join('resources', 'sample.json'))).read()

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictEqual(json.loads(json_str), json.loads(response.content))
