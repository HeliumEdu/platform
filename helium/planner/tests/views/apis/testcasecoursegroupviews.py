import datetime
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup
from helium.planner.tests.helpers import coursegrouphelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourseGroupViews(TestCase):
    def test_coursegroup_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_list')),
            self.client.post(reverse('api_planner_coursegroups_list')),
            self.client.get(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_coursegroups(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        coursegrouphelper.given_course_group_exists(user1)
        coursegrouphelper.given_course_group_exists(user2)
        coursegrouphelper.given_course_group_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroups_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseGroup.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_coursegroup(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'start_date': '2015-03-05',
            'end_date': '2015-07-09',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('api_planner_coursegroups_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CourseGroup.objects.count(), 1)
        course_group = CourseGroup.objects.get(pk=response.data['id'])
        data.update({'user': user.pk})
        coursegrouphelper.verify_course_group_matches_data(self, course_group, data)
        coursegrouphelper.verify_course_group_matches_data(self, course_group, response.data)

    def test_get_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course_group.average_grade = 87.66
        course_group.trend = 0.65
        course_group.save()

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        coursegrouphelper.verify_course_group_matches_data(self, course_group, response.data)
        self.assertEqual(course_group.num_items, response.data['num_items'])
        self.assertEqual(course_group.num_complete, response.data['num_complete'])
        self.assertEqual(course_group.num_incomplete, response.data['num_incomplete'])
        self.assertEqual(course_group.num_graded, response.data['num_graded'])

    def test_update_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        self.assertEqual(course_group.title, 'Test Course Group')
        self.assertTrue(course_group.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False,
            # Intentionally NOT changing these value
            'start_date': course_group.start_date.isoformat(),
            'end_date': course_group.end_date.isoformat()
        }
        response = self.client.put(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        coursegrouphelper.verify_course_group_matches_data(self, course_group, response.data)

    def test_delete_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CourseGroup.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(CourseGroup.objects.count(), 0)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk})),
            self.client.put(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk})),
            self.client.delete(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk}))
        ]

        # THEN
        self.assertTrue(CourseGroup.objects.filter(pk=course_group.pk, user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user2)
        average_grade = course_group.average_grade
        trend = course_group.trend
        private_slug = course_group.private_slug

        # WHEN
        data = {
            'average_grade': 23,
            'trend': 1.5,
            'private_slug': 'new_slug',
            'user': user1.pk,
            # Intentionally NOT changing these value
            'title': course_group.title,
            'start_date': course_group.start_date.isoformat(),
            'end_date': course_group.end_date.isoformat()
        }
        response = self.client.put(reverse('api_planner_coursegroups_detail', kwargs={'pk': course_group.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_group = CourseGroup.objects.get(pk=course_group.id)
        self.assertEqual(course_group.average_grade, average_grade)
        self.assertEqual(course_group.trend, trend)
        self.assertEqual(course_group.private_slug, private_slug)
        self.assertEqual(course_group.get_user().pk, user2.pk)

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        responses = [
            self.client.get(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_detail', kwargs={'pk': '9999'}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        coursegrouphelper.given_course_group_exists(user,
                                                    start_date=datetime.date(2016, 5, 8),
                                                    end_date=datetime.date(2016, 8, 15))
        course_group2 = coursegrouphelper.given_course_group_exists(user,
                                                                    start_date=datetime.date(2016, 8, 15),
                                                                    end_date=datetime.date(2016, 11, 20))
        course_group3 = coursegrouphelper.given_course_group_exists(user,
                                                                    start_date=datetime.date(2017, 1, 8),
                                                                    end_date=datetime.date(2017, 3, 25))
        coursegrouphelper.given_course_group_exists(user,
                                                    start_date=datetime.date(2017, 3, 25),
                                                    end_date=datetime.date(2017, 8, 15))

        response = self.client.get(
            reverse('api_planner_coursegroups_list') + '?start_date__gte={}&end_date__lte={}'.format(
                course_group2.start_date.isoformat(),
                course_group3.end_date.isoformat()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
