"""
Tests for Category interaction.
"""
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Category
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseCategory(TestCase):
    def test_course_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_categories_list')),
            self.client.post(reverse('api_planner_categories_list')),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                     kwargs={'course_group_id': '9999', 'course_id': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999', 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group_id': '9999', 'course_id': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_categories(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        categoryhelper.given_category_exists(course1)
        categoryhelper.given_category_exists(course2)
        categoryhelper.given_category_exists(course3)
        categoryhelper.given_category_exists(course3)

        # WHEN
        response1 = self.client.get(reverse('api_planner_categories_list'))
        response2 = self.client.get(
            reverse('api_planner_coursegroups_courses_categories_lc',
                    kwargs={'course_group_id': course_group2.pk, 'course_id': course3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_category(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'title': 'some title',
            'weight': 25,
            'color': '#7bd148'
        }
        response = self.client.post(
            reverse('api_planner_coursegroups_courses_categories_lc',
                    kwargs={'course_group_id': course_group.pk, 'course_id': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 1)
        category = Category.objects.get(pk=response.data['id'])
        categoryhelper.verify_category_matches_data(self, category, response.data)

    def test_get_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group_id': course_group.pk, 'course_id': course.pk,
                                                   'pk': category.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        categoryhelper.verify_category_matches_data(self, category, response.data)

    def test_update_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        data = {
            'title': 'some title',
            'weight': 25,
            'color': '#7bd148'
        }
        response = self.client.put(
            reverse('api_planner_coursegroups_courses_categories_detail',
                    kwargs={'course_group_id': course_group.pk, 'course_id': course.pk, 'pk': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(float(response.data['weight']), data['weight'])
        self.assertEqual(response.data['color'], data['color'])
        category = Category.objects.get(pk=category.pk)
        self.assertEqual(category.title, response.data['title'])
        self.assertEqual(category.weight, float(response.data['weight']))
        self.assertEqual(category.color, response.data['color'])

    def test_delete_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroups_courses_categories_detail',
                                              kwargs={'course_group_id': course_group.pk, 'course_id': course.pk,
                                                      'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())
        self.assertEqual(Category.objects.count(), 0)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        category = categoryhelper.given_category_exists(course1)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': course_group1.pk, 'course_id': course1.pk})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                     kwargs={'course_group_id': course_group1.pk, 'course_id': course1.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': course_group2.pk, 'course_id': course1.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': course_group1.pk, 'course_id': course1.pk,
                                            'pk': category.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': course_group1.pk, 'course_id': course1.pk,
                                            'pk': category.pk})),
            self.client.delete(reverse('api_planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group_id': course_group1.pk, 'course_id': course1.pk,
                                               'pk': category.pk}))
        ]

        # THEN
        self.assertTrue(Category.objects.filter(pk=category.pk, course__course_group__user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course2)
        average_grade = category.average_grade
        grade_by_weight = category.grade_by_weight
        trend = category.trend

        # WHEN
        data = {
            'average_grade': 23,
            'grade_by_weight': 56,
            'trend': 1.5,
            'course': course1.pk,
            # Intentionally NOT changing these value
            'title': category.title,
            'weight': category.weight,
            'color': category.color
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group_id': course_group.pk, 'course_id': course2.pk,
                                                   'pk': category.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category = Category.objects.get(id=category.id)
        self.assertEqual(category.average_grade, average_grade)
        self.assertEqual(category.grade_by_weight, grade_by_weight)
        self.assertEqual(category.trend, trend)
        self.assertEqual(category.course.pk, course2.pk)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'color': 'invalid-hex',
        }
        response = self.client.post(
            reverse('api_planner_coursegroups_courses_categories_lc',
                    kwargs={'course_group_id': course_group.pk, 'course_id': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('color', response.data)
        self.assertEqual(Category.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        color = category.color

        # WHEN
        data = {
            'color': 'invalid-hex',
            # Intentionally NOT changing these value
            'title': category.title,
            'weight': category.weight,
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group_id': course_group.pk, 'course_id': course.pk,
                                                   'pk': category.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('color', response.data)
        category = Category.objects.get(id=category.id)
        self.assertEqual(category.color, color)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                     kwargs={'course_group_id': course_group.pk, 'course_id': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                     kwargs={'course_group_id': '9999', 'course_id': course.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': course_group.pk, 'course_id': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': course_group.pk, 'course_id': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': '9999', 'course_id': course.pk})),
            self.client.post(reverse('api_planner_coursegroups_courses_categories_lc',
                                    kwargs={'course_group_id': '9999', 'course_id': course.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': course_group.pk, 'course_id': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': course_group.pk, 'course_id': '9999', 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': course.pk, 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': course.pk, 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999', 'pk': category.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group_id': '9999', 'course_id': '9999', 'pk': category.pk}))
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('not found', response.data['detail'].lower())
