"""
Tests for CourseGroup interaction.
"""
from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourseGroup(TestCase):
    def test_coursegroup_login_required(self):
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

    def test_get_coursegroups(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        coursegrouphelper.given_course_group_exists(user1)
        coursegrouphelper.given_course_group_exists(user2)
        coursegrouphelper.given_course_group_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroup_list'))

        # THEN
        self.assertEqual(len(response.data), 2)
