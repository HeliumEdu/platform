__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Category
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, categoryhelper, homeworkhelper


class TestCaseCategoryViews(APITestCase):
    def test_category_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_categories_list')),
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_categories(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        categoryhelper.given_category_exists(course1)
        categoryhelper.given_category_exists(course2, title='Test Category 2')
        categoryhelper.given_category_exists(course3, title='Test Category 3')
        categoryhelper.given_category_exists(course3, title='Test Category 4')

        # WHEN
        response1 = self.client.get(reverse('planner_categories_list'))
        response2 = self.client.get(
            reverse('planner_coursegroups_courses_categories_list',
                    kwargs={'course_group': course_group2.pk, 'course': course3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Category.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_category(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'title': 'some title',
            'weight': 25,
            'color': '#7bd148',
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'average_grade': -1,
            'grade_by_weight': 0,
            'trend': None
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_categories_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 1)
        category = Category.objects.get(pk=response.data['id'])
        categoryhelper.verify_category_matches_data(self, category, data)
        categoryhelper.verify_category_matches_data(self, category, response.data)

    def test_create_category_exceeds_weight_course_100_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, weight=25)
        categoryhelper.given_category_exists(course, title='Test Category 2', weight=25)
        categoryhelper.given_category_exists(course, title='Test Category 3', weight=25)
        categoryhelper.given_category_exists(course, title='Test Category 4', weight=25)

        # WHEN
        data = {
            'title': 'some title',
            'weight': 0.0000000001,
            'color': '#7bd148'
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_categories_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('weight', response.data)
        self.assertEqual(Category.objects.count(), 4)

    def test_get_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        homeworkhelper.given_homework_exists(course, category=category)
        homeworkhelper.given_homework_exists(course, completed=True, category=category)
        homeworkhelper.given_homework_exists(course, completed=True, current_grade='25/30', category=category)

        # WHEN
        response = self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': category.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category = Category.objects.get(pk=category.pk)
        categoryhelper.verify_category_matches_data(self, category, response.data)
        self.assertEqual(response.data['num_homework'], 3)
        self.assertEqual(response.data['num_homework_graded'], 1)

    def test_update_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        data = {
            'title': 'some title',
            'weight': '25.00',
            'color': '#7bd148'
        }
        response = self.client.put(
            reverse('planner_coursegroups_courses_categories_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': category.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        category = Category.objects.get(pk=category.pk)
        categoryhelper.verify_category_matches_data(self, category, response.data)

    def test_update_category_exceeds_weight_course_100_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        categoryhelper.given_category_exists(course, weight=25)
        categoryhelper.given_category_exists(course, title='Test Category 2', weight=25)
        categoryhelper.given_category_exists(course, title='Test Category 3', weight=25)
        category = categoryhelper.given_category_exists(course, title='Test Category 4', weight=25)

        # WHEN
        data = {
            'title': 'some title',
            'weight': 25.0000000001,
            'color': '#7bd148'
        }
        response = self.client.put(
            reverse('planner_coursegroups_courses_categories_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': category.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('weight', response.data)

    def test_delete_category_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': category.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Category.objects.filter(pk=category.pk).exists())

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        category = categoryhelper.given_category_exists(course1)

        # WHEN
        responses = [
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': course_group1.pk, 'course': course1.pk})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course1.pk})),
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': course_group2.pk, 'course': course1.pk})),
            self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': course_group1.pk, 'course': course1.pk,
                                            'pk': category.pk})),
            self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': course_group1.pk, 'course': course1.pk,
                                            'pk': category.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group': course_group1.pk, 'course': course1.pk,
                                               'pk': category.pk}))
        ]

        # THEN
        self.assertTrue(Category.objects.filter(pk=category.pk, course__course_group__user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
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
        response = self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course2.pk,
                                                   'pk': category.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category = Category.objects.get(pk=category.id)
        self.assertEqual(category.average_grade, average_grade)
        self.assertEqual(category.grade_by_weight, grade_by_weight)
        self.assertEqual(category.trend, trend)
        self.assertEqual(category.course.pk, course2.pk)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'color': 'invalid-hex',
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_categories_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('color', response.data)
        self.assertEqual(Category.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        # WHEN
        data = {
            'color': 'invalid-hex'
        }
        response = self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': category.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('color', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)

        responses = [
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': course_group.pk, 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': '9999', 'course': course.pk})),
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': course_group.pk, 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': course_group.pk, 'course': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_categories_list',
                                    kwargs={'course_group': '9999', 'course': course.pk})),
            self.client.post(reverse('planner_coursegroups_courses_categories_list',
                                     kwargs={'course_group': '9999', 'course': course.pk})),
            self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': category.pk})),
            self.client.put(reverse('planner_coursegroups_courses_categories_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': category.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_categories_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': category.pk}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())
