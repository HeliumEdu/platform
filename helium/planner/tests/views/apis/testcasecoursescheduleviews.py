__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.planner.models import CourseSchedule
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper


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
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

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
        courseschedulehelper.given_course_schedule_exists(course1)
        courseschedulehelper.given_course_schedule_exists(course2)
        courseschedulehelper.given_course_schedule_exists(course3)

        # WHEN
        response = self.client.get(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group3.pk, 'course': course3.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(CourseSchedule.objects.count(), 3)
        self.assertEqual(len(response.data), 1)

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

    def test_create_course_schedule_no_many(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

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
            'sat_end_time': '12:00:00'
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(CourseSchedule.objects.count(), 1)

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
        course_schedule.refresh_from_db()
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
        course_schedule.refresh_from_db()
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

    def test_no_access_object_owned_by_another_user(self):
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

    def test_create_start_time_after_end_time(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'days_of_week': '0100000',
            'mon_start_time': '15:30:00',
            'mon_end_time': '14:30:00',  # End before start
            # These fields are set to their defaults
            'sun_start_time': '12:00:00',
            'sun_end_time': '12:00:00',
            'tue_start_time': '12:00:00',
            'tue_end_time': '12:00:00',
            'wed_start_time': '12:00:00',
            'wed_end_time': '12:00:00',
            'thu_start_time': '12:00:00',
            'thu_end_time': '12:00:00',
            'fri_start_time': '12:00:00',
            'fri_end_time': '12:00:00',
            'sat_start_time': '12:00:00',
            'sat_end_time': '12:00:00',
        }
        response = self.client.post(
            reverse('planner_coursegroups_courses_courseschedules_list',
                    kwargs={'course_group': course_group.pk, 'course': course.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The 'start_time' of 'mon' must be before 'end_time'", str(response.data))
        self.assertEqual(CourseSchedule.objects.count(), 0)

    def test_update_start_time_after_end_time(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        data = {
            'days_of_week': '0001000',
            'wed_start_time': '19:30:00',
            'wed_end_time': '18:30:00',  # End before start
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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The 'start_time' of 'wed' must be before 'end_time'", str(response.data))

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
                self.assertIn('matches the given query', response.data['detail'].lower())

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        schedule1 = courseschedulehelper.given_course_schedule_exists(course)
        schedule2 = courseschedulehelper.given_course_schedule_exists(course, days_of_week='0010000')
        schedule3 = courseschedulehelper.given_course_schedule_exists(course, days_of_week='0001000')

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        CourseSchedule.objects.filter(pk=schedule1.pk).update(updated_at=old_time)
        CourseSchedule.objects.filter(pk=schedule2.pk).update(updated_at=recent_time)
        CourseSchedule.objects.filter(pk=schedule3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_courseschedules_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(schedule2.pk, returned_ids)
        self.assertIn(schedule3.pk, returned_ids)
        self.assertNotIn(schedule1.pk, returned_ids)
