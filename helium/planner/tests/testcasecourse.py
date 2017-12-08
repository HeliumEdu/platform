"""
Tests for Course interaction.
"""
import json

from dateutil import parser
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Course
from helium.planner.tests.helpers import coursegrouphelper, coursehelper

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
                reverse('api_planner_coursegroups_courses_lc', kwargs={'course_group_id': course_group3.pk}))

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
            'wed_end_time_alt': '19:30:00'
        }
        response = self.client.post(
                reverse('api_planner_coursegroups_courses_lc', kwargs={'course_group_id': course_group.pk}),
                json.dumps(data),
                content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Course.objects.count(), 1)
        course = Course.objects.get(pk=response.data['id'])
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
                                           kwargs={'course_group_id': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        coursehelper.verify_course_matches_data(self, course, response.data)

    def test_update_course_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

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
            'wed_end_time_alt': '19:30:00'
        }
        response = self.client.put(
                reverse('api_planner_coursegroups_courses_detail',
                        kwargs={'course_group_id': course_group.pk, 'pk': course.pk}),
                json.dumps(data),
                content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['room'], data['room'])
        self.assertEqual(float(response.data['credits']), data['credits'])
        self.assertEqual(response.data['color'], data['color'])
        self.assertEqual(response.data['website'], data['website'])
        self.assertEqual(response.data['is_online'], data['is_online'])
        self.assertEqual(response.data['teacher_name'], data['teacher_name'])
        self.assertEqual(response.data['teacher_email'], data['teacher_email'])
        self.assertEqual(response.data['start_date'], data['start_date'])
        self.assertEqual(response.data['end_date'], data['end_date'])
        self.assertEqual(response.data['days_of_week'], data['days_of_week'])
        self.assertEqual(response.data['mon_start_time'], data['mon_start_time'])
        self.assertEqual(response.data['mon_end_time'], data['mon_end_time'])
        self.assertEqual(response.data['wed_start_time'], data['wed_start_time'])
        self.assertEqual(response.data['wed_end_time'], data['wed_end_time'])
        self.assertEqual(response.data['fri_start_time'], data['fri_start_time'])
        self.assertEqual(response.data['fri_end_time'], data['fri_end_time'])
        self.assertEqual(response.data['days_of_week_alt'], data['days_of_week_alt'])
        self.assertEqual(response.data['wed_start_time_alt'], data['wed_start_time_alt'])
        self.assertEqual(response.data['wed_end_time_alt'], data['wed_end_time_alt'])
        course_group = Course.objects.get(pk=course.pk)
        self.assertEqual(course_group.title, response.data['title'])
        self.assertEqual(course_group.room, response.data['room'])
        self.assertEqual(course_group.credits, float(response.data['credits']))
        self.assertEqual(course_group.color, response.data['color'])
        self.assertEqual(course_group.website, response.data['website'])
        self.assertEqual(course_group.is_online, response.data['is_online'])
        self.assertEqual(course_group.teacher_name, response.data['teacher_name'])
        self.assertEqual(course_group.teacher_email, response.data['teacher_email'])
        self.assertEqual(course_group.start_date, parser.parse(response.data['start_date']).date())
        self.assertEqual(course_group.end_date, parser.parse(response.data['end_date']).date())
        self.assertEqual(course_group.days_of_week, response.data['days_of_week'])
        self.assertEqual(course_group.mon_start_time, parser.parse(response.data['mon_start_time']).time())
        self.assertEqual(course_group.mon_end_time, parser.parse(response.data['mon_end_time']).time())
        self.assertEqual(course_group.wed_start_time, parser.parse(response.data['wed_start_time']).time())
        self.assertEqual(course_group.wed_end_time, parser.parse(response.data['wed_end_time']).time())
        self.assertEqual(course_group.fri_start_time, parser.parse(response.data['fri_start_time']).time())
        self.assertEqual(course_group.fri_end_time, parser.parse(response.data['fri_end_time']).time())
        self.assertEqual(course_group.days_of_week_alt, response.data['days_of_week_alt'])
        self.assertEqual(course_group.wed_start_time_alt, parser.parse(response.data['wed_start_time_alt']).time())
        self.assertEqual(course_group.wed_end_time_alt, parser.parse(response.data['wed_end_time_alt']).time())

    def test_delete_course_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                              kwargs={'course_group_id': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Course.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(Course.objects.count(), 0)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        response1 = self.client.get(reverse('api_planner_coursegroups_courses_lc',
                                            kwargs={'course_group_id': course_group.pk}))
        response2 = self.client.post(reverse('api_planner_coursegroups_courses_lc',
                                             kwargs={'course_group_id': course_group.pk}))
        response3 = self.client.get(reverse('api_planner_coursegroups_courses_detail',
                                            kwargs={'course_group_id': course_group.pk, 'pk': course.pk}))
        response4 = self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                            kwargs={'course_group_id': course_group.pk, 'pk': course.pk}))
        response5 = self.client.delete(reverse('api_planner_coursegroups_courses_detail',
                                               kwargs={'course_group_id': course_group.pk, 'pk': course.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response2.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response3.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response4.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response5.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Course.objects.filter(pk=course.pk).exists())
        self.assertEqual(Course.objects.count(), 1)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group1 = coursegrouphelper.given_course_group_exists(user)
        course_group2 = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group2)
        current_grade = course.current_grade
        trend = course.trend
        private_slug = course.private_slug

        # WHEN
        data = {
            'current_grade': 23,
            'trend': 1.5,
            'private_slug': 'new_slug',
            'course_group': course_group1.pk,
            # Intentionally NOT changing these value
            'credits': course.credits,
            'start_date': course.start_date.isoformat(),
            'end_date': course.end_date.isoformat()
        }
        response = self.client.put(reverse('api_planner_coursegroups_courses_detail',
                                           kwargs={'course_group_id': course_group2.pk, 'pk': course.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course = Course.objects.get(id=course.id)
        self.assertEqual(course.current_grade, current_grade)
        self.assertEqual(course.trend, trend)
        self.assertEqual(course.private_slug, private_slug)
        self.assertEqual(course.course_group.pk, course_group2.pk)
