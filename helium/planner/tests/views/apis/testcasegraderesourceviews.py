from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper

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
        course_group1 = coursegrouphelper.given_course_group_exists(user)
        course_group2 = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        category1 = categoryhelper.given_category_exists(course1, weight=50)
        category2 = categoryhelper.given_category_exists(course1, weight=50)
        # This category having no weight will result in the course not having weighted grading
        category3 = categoryhelper.given_category_exists(course2, weight=0)
        homework1 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='25/30')
        homework2 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='30/40')
        homework3 = homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                                         current_grade='80/90')
        homework4 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='5/6')
        homework5 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='25/30')
        # Incomplete homework are not graded
        homework6 = homeworkhelper.given_homework_exists(course1, category=category2, current_grade='-1/100')
        # Completed homework with no grade set are not graded
        homework7 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('api_planner_resource_grades'))

        # THEN
        self.assertEquals(len(response.data['course_groups']), 2)
        self.assertEquals(len(response.data['course_groups'][0]['courses']), 1)
        self.assertEquals(len(response.data['course_groups'][1]['courses']), 1)
        self.assertEquals(len(response.data['course_groups'][0]['courses'][0]['categories']), 2)
        self.assertEquals(len(response.data['course_groups'][1]['courses'][0]['categories']), 1)
        # TODO: add grading assertions after grade implementation is complete
