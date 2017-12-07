"""
Tests for Course interaction.
"""

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourse(TestCase):
    def test_course_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.get(reverse('api_planner_courses_list'))
        response2 = self.client.get(reverse('api_planner_coursegroups_courses_lc', kwargs={'course_group_id': 1}))
        response3 = self.client.get(
                reverse('api_planner_coursegroups_courses_detail', kwargs={'course_group_id': 1, 'pk': 1}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)
