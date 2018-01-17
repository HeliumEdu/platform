from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseEventViews(TestCase):
    def test_grade_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_resource_grades'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_grades(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        # TODO: add grades

        # WHEN
        response = self.client.get(reverse('api_planner_resource_grades'))

        # THEN
        # TODO: add assertions after grade implementation is complete
