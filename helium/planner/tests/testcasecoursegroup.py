"""
Tests for CourseGroup interaction.
"""
from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourseGroup(TestCase):
    def test_externalcalendar_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.get(reverse('api_planner_coursegroup_list'))
        response2 = self.client.get(reverse('api_planner_coursegroup_detail', kwargs={'pk': 1}))

        # THEN
        self.assertEqual(response1.status_code, 302)
        self.assertRedirects(response1, '/login?next={}'.format(reverse('api_planner_coursegroup_list')))
        self.assertEqual(response2.status_code, 302)
        self.assertRedirects(response2,
                             '/login?next={}'.format(reverse('api_planner_coursegroup_detail', kwargs={'pk': 1})))
