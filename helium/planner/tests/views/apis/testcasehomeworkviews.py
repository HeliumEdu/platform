from future.standard_library import install_aliases

install_aliases()

import json

import datetime
from urllib.parse import quote

from django.utils import timezone
from django.test import TestCase
from rest_framework import status
from rest_framework.reverse import reverse

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Homework
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, homeworkhelper, categoryhelper, \
    materialgrouphelper, materialhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseHomeworkViews(TestCase):
    def test_homework_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_homework_list')),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_homework(self):
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        homeworkhelper.given_homework_exists(course1)
        homeworkhelper.given_homework_exists(course2)
        homeworkhelper.given_homework_exists(course3)
        homeworkhelper.given_homework_exists(course3)

        # WHEN
        response1 = self.client.get(reverse('api_planner_homework_list'))
        response2 = self.client.get(
            reverse('api_planner_coursegroups_courses_homework_list',
                    kwargs={'course_group': course_group2.pk, 'course': course3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Homework.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertIn('course_group', response1.data[0]['course'])
        self.assertEqual(len(response2.data), 2)

    def test_create_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'priority': 12,
            'comments': 'some comment',
            'current_grade': '25/30',
            'completed': False,
            'category': category.pk,
            'materials': [material.pk],
            'course': course.pk
        }
        response = self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Homework.objects.count(), 1)
        homework = Homework.objects.get(pk=response.data['id'])
        homeworkhelper.verify_homework_matches_data(self, homework, data)
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_get_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': homework.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_update_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category1 = categoryhelper.given_category_exists(course)
        category2 = categoryhelper.given_category_exists(course)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material1 = materialhelper.given_material_exists(material_group)
        material2 = materialhelper.given_material_exists(material_group)
        homework = homeworkhelper.given_homework_exists(course, category=category1, materials=[material1])

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-08T14:00:00Z',
            'priority': 12,
            'comments': 'some comment',
            'current_grade': '33/40',
            'completed': True,
            'category': category2.pk,
            'materials': [material2.pk],
            'course': course.pk
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': homework.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        homework = Homework.objects.get(pk=homework.pk)
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_delete_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': homework.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Homework.objects.filter(pk=homework.pk).exists())
        self.assertEqual(Homework.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user1')
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        materialgroup2 = materialgrouphelper.given_material_group_exists(user2)
        material2 = materialhelper.given_material_exists(materialgroup2)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        category2 = categoryhelper.given_category_exists(course2)
        homework = homeworkhelper.given_homework_exists(course1)

        # WHEN
        responses = [
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course2.pk}),
                             json.dumps({}),
                             content_type='application/json'),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course1.pk}),
                             json.dumps({'category': category2.pk}),
                             content_type='application/json'),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course1.pk}),
                             json.dumps({'materials': [material2.pk]}),
                             content_type='application/json'),
            self.client.put(
                reverse('api_planner_coursegroups_courses_homework_detail',
                        kwargs={'course_group': course_group1.pk, 'course': course1.pk, 'pk': homework.pk}),
                json.dumps({'course': course2.pk}),
                content_type='application/json'),
            self.client.put(
                reverse('api_planner_coursegroups_courses_homework_detail',
                        kwargs={'course_group': course_group1.pk, 'course': course1.pk, 'pk': homework.pk}),
                json.dumps({'materials': [material2.pk]}),
                content_type='application/json'),
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk})),
            self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': course_group.pk, 'course': course.pk,
                                               'pk': homework.pk}))
        ]

        # THEN
        self.assertTrue(Homework.objects.filter(pk=homework.pk, course__course_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': homework.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group.pk, 'course': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': '9999', 'course': course.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk})),
            self.client.delete(reverse('api_planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course,
                                             start=datetime.datetime(2014, 5, 8, 16, 0, 0,
                                                                     tzinfo=timezone.utc),
                                             end=datetime.datetime(2014, 5, 8, 17, 0, 0,
                                                                   tzinfo=timezone.utc))
        homework2 = homeworkhelper.given_homework_exists(course,
                                                         start=datetime.datetime(2014, 5, 8, 17, 0, 0,
                                                                                 tzinfo=timezone.utc),
                                                         end=datetime.datetime(2014, 5, 8, 18, 0, 0,
                                                                               tzinfo=timezone.utc))
        homework3 = homeworkhelper.given_homework_exists(course,
                                                         start=datetime.datetime(2014, 5, 8, 18, 30, 0,
                                                                                 tzinfo=timezone.utc),
                                                         end=datetime.datetime(2014, 5, 8, 19, 0, 0,
                                                                               tzinfo=timezone.utc))
        homeworkhelper.given_homework_exists(course,
                                             start=datetime.datetime(2014, 5, 8, 19, 30, 0,
                                                                     tzinfo=timezone.utc),
                                             end=datetime.datetime(2014, 5, 8, 21, 0, 0,
                                                                   tzinfo=timezone.utc))

        response = self.client.get(
            reverse('api_planner_homework_list') + '?start={}&end={}'.format(quote(homework2.start.isoformat()),
                                                                             quote(homework3.end.isoformat())))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_title_search_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course, title='test1')
        homeworkhelper.given_homework_exists(course, title='test2')

        response = self.client.get(reverse('api_planner_homework_list') + '?search=test1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_course_search_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group, title='testcourse')
        course2 = coursehelper.given_course_exists(course_group, title='othercourse')
        homework = homeworkhelper.given_homework_exists(course1, title='test1')
        homeworkhelper.given_homework_exists(course2, title='test2')

        response = self.client.get(reverse('api_planner_homework_list') + '?search=testcourse')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_category_search_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        category = categoryhelper.given_category_exists(course, title='testcategory')
        homework = homeworkhelper.given_homework_exists(course, title='test1', category=category)
        homeworkhelper.given_homework_exists(course, title='test2')

        response = self.client.get(reverse('api_planner_homework_list') + '?search=testcategory')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)
