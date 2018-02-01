from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'


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
                                                         current_grade='20/30')
        homework2 = homeworkhelper.given_homework_exists(course1, category=category1, completed=True,
                                                         current_grade='25/30')
        homework3 = homeworkhelper.given_homework_exists(course1, category=category2, completed=True,
                                                         current_grade='15/30')
        homework4 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='20/30')
        homework5 = homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                                         current_grade='25/30')
        # Incomplete homework are not graded
        homeworkhelper.given_homework_exists(course1, category=category2, current_grade='-1/100')
        # Completed homework with no grade set are not graded
        homeworkhelper.given_homework_exists(course2, category=category3, completed=True,
                                             current_grade='-1/100')

        # WHEN
        response = self.client.get(reverse('api_planner_resource_grades'))

        # THEN
        self.assertEquals(len(response.data['course_groups']), 2)
        self.assertEquals(len(response.data['course_groups'][0]['courses']), 1)
        self.assertEquals(len(response.data['course_groups'][1]['courses']), 1)
        self.assertEquals(len(response.data['course_groups'][0]['courses'][0]['categories']), 2)
        self.assertEquals(len(response.data['course_groups'][1]['courses'][0]['categories']), 1)
        self.assertEquals(len(response.data['course_groups'][0]['courses'][0]['grade_points']), 3)
        self.assertEquals(len(response.data['course_groups'][1]['courses'][0]['grade_points']), 2)

        self.assertIn('title', response.data['course_groups'][0])
        self.assertEquals(float(response.data['course_groups'][0]['overall_grade']), 62.5)
        self.assertIn('trend', response.data['course_groups'][0])
        self.assertIn('num_graded', response.data['course_groups'][0])

        self.assertIn('title', response.data['course_groups'][0]['courses'][0])
        self.assertEquals(float(response.data['course_groups'][0]['courses'][0]['overall_grade']), 62.5)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0])
        self.assertIn('num_graded', response.data['course_groups'][0]['courses'][0])
        self.assertIn('has_weighted_grading', response.data['course_groups'][0]['courses'][0])

        grade_points = response.data['course_groups'][0]['courses'][0]['grade_points']
        self.assertEquals(grade_points[0][0], homework1.start)
        self.assertEquals(grade_points[0][1], 66.6667)
        self.assertEquals(grade_points[1][0], homework2.start)
        self.assertEquals(grade_points[1][1], 75.0)
        self.assertEquals(grade_points[2][0], homework3.start)
        self.assertEquals(grade_points[2][1], 66.6667)

        self.assertIn('title', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertEquals(float(response.data['course_groups'][0]['courses'][0]['categories'][0]['overall_grade']),
                          75.0)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('num_graded', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('weight', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('color', response.data['course_groups'][0]['courses'][0]['categories'][0])
        self.assertIn('grade_by_weight', response.data['course_groups'][0]['courses'][0]['categories'][0])

        self.assertIn('title', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertEquals(float(response.data['course_groups'][0]['courses'][0]['categories'][1]['overall_grade']),
                          50.0)
        self.assertIn('trend', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('num_graded', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('weight', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('color', response.data['course_groups'][0]['courses'][0]['categories'][1])
        self.assertIn('grade_by_weight', response.data['course_groups'][0]['courses'][0]['categories'][1])

        self.assertIn('title', response.data['course_groups'][1])
        self.assertEquals(float(response.data['course_groups'][1]['overall_grade']), 75.0)
        self.assertIn('trend', response.data['course_groups'][1])
        self.assertIn('num_graded', response.data['course_groups'][1])

        self.assertIn('title', response.data['course_groups'][1]['courses'][0])
        self.assertEquals(float(response.data['course_groups'][1]['courses'][0]['overall_grade']), 75.0)
        self.assertIn('trend', response.data['course_groups'][1]['courses'][0])
        self.assertIn('num_graded', response.data['course_groups'][1]['courses'][0])
        self.assertIn('has_weighted_grading', response.data['course_groups'][1]['courses'][0])

        grade_points = response.data['course_groups'][1]['courses'][0]['grade_points']
        self.assertEquals(grade_points[0][0], homework4.start)
        self.assertEquals(grade_points[0][1], 66.6667)
        self.assertEquals(grade_points[1][0], homework5.start)
        self.assertEquals(grade_points[1][1], 75.0)

        self.assertIn('title', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertEquals(float(response.data['course_groups'][1]['courses'][0]['categories'][0]['overall_grade']),
                          75.0)
        self.assertIn('trend', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('num_graded', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('weight', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('color', response.data['course_groups'][1]['courses'][0]['categories'][0])
        self.assertIn('grade_by_weight', response.data['course_groups'][1]['courses'][0]['categories'][0])
