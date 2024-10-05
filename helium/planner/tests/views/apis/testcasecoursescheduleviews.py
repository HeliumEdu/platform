__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.planner.models import CourseSchedule
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"
class TestCaseCourseViews(APITestCase, CacheTestCase):
    def test_course_schedule_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_courseschedules_list',
                                     kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.get(
                reverse('planner_coursegroups_courses_courseschedules_detail',
                        kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.put(
                reverse('planner_coursegroups_courses_courseschedules_detail',
                        kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.delete(
                reverse('planner_coursegroups_courses_courseschedules_detail',
                        kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_course_schedules(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course_group3 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group3)
        course4 = coursehelper.given_course_exists(course_group3)
        courseschedulehelper.given_course_schedule_exists(course1)
        courseschedulehelper.given_course_schedule_exists(course2)
        courseschedulehelper.given_course_schedule_exists(course3)
        courseschedulehelper.given_course_schedule_exists(course4)
        courseschedulehelper.given_course_schedule_exists(course4)

        # WHEN
        response = self.client.get(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group3.pk, 'course': course4.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseSchedule.objects.count(), 5)
        self.assertEqual(len(response.data), 2)

    def test_create_course_schedule(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'days_of_week': '0101010',
            'mon_start_time': '14:30:00',
            'mon_end_time': '15:30:00',
            'wed_start_time': '14:30:00',
            'wed_end_time': '15:30:00',
            'fri_start_time': '14:30:00',
            'fri_end_time': '15:30:00',
            # These fields are set to their defaults
            'sun_start_time': '12:00:00',
            'sun_end_time': '12:00:00',
            'tue_start_time': '12:00:00',
            'tue_end_time': '12:00:00',
            'thu_start_time': '12:00:00',
            'thu_end_time': '12:00:00',
            'sat_start_time': '12:00:00',
            'sat_end_time': '12:00:00',
            'course': course.pk,
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CourseSchedule.objects.count(), 1)
        course_schedule = CourseSchedule.objects.get(pk=response.data['id'])
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule, data)
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule, response.data)

    def test_get_course_schedule_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        response = self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': course_schedule.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        course_schedule = CourseSchedule.objects.get(pk=course_schedule.pk)
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule, response.data)

    def test_update_course_schedule_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        data = {
            'days_of_week': '0001000',
            'wed_start_time': '18:30:00',
            'wed_end_time': '19:30:00',
            # These fields are set to their defaults
            'sun_start_time': '12:00:00',
            'sun_end_time': '12:00:00',
            'mon_start_time': '12:00:00',
            'mon_end_time': '12:00:00',
            'tue_start_time': '12:00:00',
            'tue_end_time': '12:00:00',
            'thu_start_time': '12:00:00',
            'thu_end_time': '12:00:00',
            'fri_start_time': '12:00:00',
            'fri_end_time': '12:00:00',
            'sat_start_time': '12:00:00',
            'sat_end_time': '12:00:00',
        }
        response = self.client.put(
            reverse('planner_coursegroups_courses_courseschedules_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': course_schedule.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        course_schedule = CourseSchedule.objects.get(pk=course_schedule.pk)
        courseschedulehelper.verify_course_schedule_matches(self, course_schedule, response.data)

    def test_delete_course_schedule_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': course_schedule.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CourseSchedule.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(CourseSchedule.objects.count(), 0)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_list',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.post(reverse('planner_coursegroups_courses_courseschedules_list',
                                     kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk,
                                            'pk': course_schedule.pk})),
            self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk,
                                            'pk': course_schedule.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                       kwargs={'course_group': course_group.pk, 'course': course.pk,
                                               'pk': course_schedule.pk}))
        ]

        # THEN
        self.assertTrue(
            CourseSchedule.objects.filter(pk=course_schedule.pk, course__course_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'sun_start_time': 'not-a-valid-date',
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sun_start_time', response.data)
        self.assertEqual(CourseSchedule.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        data = {
            'sun_start_time': 'not-a-valid-time'
        }
        response = self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': course_schedule.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sun_start_time', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        responses = [
            self.client.get(
                reverse('planner_coursegroups_courses_courseschedules_list',
                        kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(
                reverse('planner_coursegroups_courses_courseschedules_list',
                        kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                       kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                       kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': course_schedule.pk})),
            self.client.put(reverse('planner_coursegroups_courses_courseschedules_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': course_schedule.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_courseschedules_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': course_schedule.pk}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())
