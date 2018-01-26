import datetime
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Course
from helium.planner.tests.helpers import coursegrouphelper, coursehelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourseViews(TestCase):
    def test_course_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_courses_list')),
            self.client.get(reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': '9999'})),
            self.client.get(
                reverse('api_planner_coursegroups_courses_detail', kwargs={'course_group': '9999', 'pk': '9999'})),
            self.client.put(
                reverse('api_planner_coursegroups_courses_detail', kwargs={'course_group': '9999', 'pk': '9999'})),
            self.client.delete(
                reverse('api_planner_coursegroups_courses_detail', kwargs={'course_group': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_courses(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course_group3 = coursegrouphelper.given_course_group_exists(user2)
        coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        coursehelper.given_course_exists(course_group3)
        coursehelper.given_course_exists(course_group3)

        # WHEN
        response1 = self.client.get(reverse('api_planner_courses_list'))
        response2 = self.client.get(
            reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': course_group3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Course.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_course(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'room': 'my room',
            'credits': 3,
            'color': '#7bd148',
            'website': 'http://www.mywebsite.com',
            'is_online': True,
            'teacher_name': 'my teacher',
            'teacher_email': 'email@teacher.com',
            'start_date': '2015-03-05',
            'end_date': '2015-07-09',
            'days_of_week': '0101010',
            'mon_start_time': '14:30:00',
            'mon_end_time': '15:30:00',
            'wed_start_time': '14:30:00',
            'wed_end_time': '15:30:00',
            'fri_start_time': '14:30:00',
            'fri_end_time': '15:30:00',
            'days_of_week_alt': '0001000',
            'wed_start_time_alt': '18:30:00',
            'wed_end_time_alt': '19:30:00',
            # These fields are set to their defaults
            'sun_start_time': '12:00:00',
            'sun_end_time': '12:00:00',
            'tue_start_time': '12:00:00',
            'tue_end_time': '12:00:00',
            'thu_start_time': '12:00:00',
            'thu_end_time': '12:00:00',
            'sat_start_time': '12:00:00',
            'sat_end_time': '12:00:00',
            'sun_start_time_alt': '12:00:00',
            'sun_end_time_alt': '12:00:00',
            'mon_start_time_alt': '12:00:00',
            'mon_end_time_alt': '12:00:00',
            'tue_start_time_alt': '12:00:00',
            'tue_end_time_alt': '12:00:00',
            'thu_start_time_alt': '12:00:00',
            'thu_end_time_alt': '12:00:00',
            'fri_start_time_alt': '12:00:00',
            'fri_end_time_alt': '12:00:00',
            'sat_start_time_alt': '12:00:00',
            'sat_end_time_alt': '12:00:00',
            'course_group': course_group.pk,
            # Read-only fields, unused in the POST but used in the validation of this dict afterward
            'current_grade': -1,
            'trend': None,
            'private_slug': None,
        }
        response = self.client.post(
            reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': course_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 1)
        course = Course.objects.get(pk=response.data['id'])
        coursehelper.verify_course_matches_data(self, course, data)
        coursehelper.verify_course_matches_data(self, course, response.data)

    def test_get_course_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course.current_grade = 87.66
        course.trend = 0.65
        course.save()

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                           kwargs={'course_group': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        coursehelper.verify_course_matches_data(self, course, response.data)
        self.assertEqual(course.num_items, response.data['num_items'])
        self.assertEqual(course.num_complete, response.data['num_complete'])
        self.assertEqual(course.num_incomplete, response.data['num_incomplete'])
        self.assertEqual(course.num_graded, response.data['num_graded'])

    def test_update_course_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group1 = coursegrouphelper.given_course_group_exists(user)
        course_group2 = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group1)

        # WHEN
        data = {
            'title': 'some title',
            'room': 'my room',
            'credits': '3.00',
            'color': '#7bd148',
            'website': 'http://www.mywebsite.com',
            'is_online': True,
            'teacher_name': 'my teacher',
            'teacher_email': 'email@teacher.com',
            'start_date': '2015-03-05',
            'end_date': '2015-07-09',
            'days_of_week': '0101010',
            'mon_start_time': '14:30:00',
            'mon_end_time': '15:30:00',
            'wed_start_time': '14:30:00',
            'wed_end_time': '15:30:00',
            'fri_start_time': '14:30:00',
            'fri_end_time': '15:30:00',
            'days_of_week_alt': '0001000',
            'wed_start_time_alt': '18:30:00',
            'wed_end_time_alt': '19:30:00',
            'course_group': course_group2.pk
        }
        response = self.client.put(
            reverse('api_planner_coursegroups_courses_detail',
                    kwargs={'course_group': course_group1.pk, 'pk': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        course = Course.objects.get(pk=course.pk)
        coursehelper.verify_course_matches_data(self, course, response.data)

    def test_delete_course_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                              kwargs={'course_group': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(Course.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user1')
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course = coursehelper.given_course_exists(course_group1)

        # WHEN
        responses = [
            self.client.post(
                reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': course_group2.pk}),
                json.dumps({}),
                content_type='application/json'),
            self.client.put(
                reverse('api_planner_coursegroups_courses_detail',
                        kwargs={'course_group': course_group1.pk, 'pk': course.pk}),
                json.dumps({'course_group': course_group2.pk}),
                content_type='application/json')
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

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_list',
                                    kwargs={'course_group': course_group.pk})),
            self.client.post(reverse('api_planner_coursegroups_courses_list',
                                     kwargs={'course_group': course_group.pk})),
            self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': course_group.pk, 'pk': course.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': course_group.pk, 'pk': course.pk})),
            self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                       kwargs={'course_group': course_group.pk, 'pk': course.pk}))
        ]

        # THEN
        self.assertTrue(Course.objects.filter(pk=course.pk, course_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        current_grade = course.current_grade
        trend = course.trend
        private_slug = course.private_slug

        # WHEN
        data = {
            'current_grade': 23,
            'trend': 1.5,
            'private_slug': 'new_slug',
            # Intentionally NOT changing these value
            'title': course.title,
            'credits': course.credits,
            'start_date': course.start_date.isoformat(),
            'end_date': course.end_date.isoformat(),
            'course_group': course.course_group.pk
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                           kwargs={'course_group': course_group.pk, 'pk': course.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course = Course.objects.get(pk=course.id)
        self.assertEqual(course.current_grade, current_grade)
        self.assertEqual(course.trend, trend)
        self.assertEqual(course.private_slug, private_slug)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)

        # WHEN
        data = {
            'start_date': 'not-a-valid-date',
        }
        response = self.client.post(
            reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': course_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)
        self.assertEqual(Course.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'start_date': 'not-a-valid-date'
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                           kwargs={'course_group': course_group.pk, 'pk': course.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start_date', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        responses = [
            self.client.get(reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': '9999'})),
            self.client.post(reverse('api_planner_coursegroups_courses_list', kwargs={'course_group': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': '9999', 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                       kwargs={'course_group': '9999', 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': course_group.pk, 'pk': '9999'})),
            self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': course_group.pk, 'pk': '9999'})),
            self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                       kwargs={'course_group': course_group.pk, 'pk': '9999'})),
            self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': '9999', 'pk': course.pk})),
            self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                    kwargs={'course_group': '9999', 'pk': course.pk})),
            self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                       kwargs={'course_group': '9999', 'pk': course.pk}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        coursehelper.given_course_exists(course_group,
                                         start_date=datetime.date(2014, 5, 8),
                                         end_date=datetime.date(2014, 8, 15))
        course2 = coursehelper.given_course_exists(course_group,
                                                   start_date=datetime.date(2014, 8, 15),
                                                   end_date=datetime.date(2014, 11, 20))
        course3 = coursehelper.given_course_exists(course_group,
                                                   start_date=datetime.date(2015, 1, 8),
                                                   end_date=datetime.date(2015, 3, 25))
        coursehelper.given_course_exists(course_group,
                                         start_date=datetime.date(2015, 3, 25),
                                         end_date=datetime.date(2015, 8, 15))

        response = self.client.get(
            reverse('api_planner_coursegroups_courses_list',
                    kwargs={'course_group': course_group.pk}) + '?start_date={}&end_date={}'.format(
                course2.start_date.isoformat(),
                course3.end_date.isoformat()))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
