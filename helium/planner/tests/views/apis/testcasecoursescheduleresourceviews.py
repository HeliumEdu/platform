import datetime

from django.urls import reverse
from mock import mock
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.test import CacheTestCase
from helium.planner.models import CourseSchedule
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, courseschedulehelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'


class TestCaseExternalCalendarResourceViews(APITestCase, CacheTestCase):
    def test_courseschedule_event_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_resource_courseschedules_events',
                                    kwargs={'course_group': '9999', 'course': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('planner_resource_courseschedules_events',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk}))
        ]

        # THEN
        self.assertTrue(
            CourseSchedule.objects.filter(pk=course_schedule.pk, course__course_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_course_schedule_as_events_db_and_cached(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        courseschedulehelper.given_course_schedule_exists(course)

        # WHEN
        response_db = self.client.get(reverse('planner_resource_courseschedules_events',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk}))
        response_cached = self.client.get(reverse('planner_resource_courseschedules_events',
                                                  kwargs={'course_group': course_group.pk, 'course': course.pk}))

        # THEN
        self.assertEqual(len(response_db.data), 53)
        self.assertEqual(response_db.data[0]['title'], course.title)
        self.assertEqual(response_db.data[0]['start'], '2017-01-06T10:30:00Z')
        self.assertEqual(response_db.data[0]['end'], '2017-01-06T13:00:00Z')
        self.assertEqual(response_db.data[0]['all_day'], False)
        self.assertEqual(response_db.data[0]['show_end_time'], True)
        self.assertEqual(response_db.data[0]['comments'],
                         '<a href="{}">{}</a> in {}'.format(course.website, course.title, course.room))
        self.assertEqual(len(response_cached.data), len(response_db.data))
        cached_event = [e for e in response_cached.data if e['id'] == response_db.data[0]['id']]
        self.assertTrue(len(cached_event) == 1)
        self.assertEqual(cached_event[0]['title'], response_db.data[0]['title'])
        self.assertEqual(cached_event[0]['start'], response_db.data[0]['start'])
        self.assertEqual(cached_event[0]['end'], response_db.data[0]['end'])
        self.assertEqual(cached_event[0]['all_day'], response_db.data[0]['all_day'])
        self.assertEqual(cached_event[0]['show_end_time'], response_db.data[0]['show_end_time'])
        self.assertEqual(cached_event[0]['comments'], response_db.data[0]['comments'])

    @mock.patch('helium.planner.services.coursescheduleservice._create_events_from_course_schedules')
    def test_course_schedule_cache_cleared_when_course_changed(self, _create_events_from_course_schedules_mock):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        course_schedule = courseschedulehelper.given_course_schedule_exists(course)
        self.client.get(reverse('planner_resource_courseschedules_events',
                                kwargs={'course_group': course_group.pk, 'course': course.pk}))
        self.assertEqual(_create_events_from_course_schedules_mock.call_count, 1)

        # WHEN
        course.start_date = datetime.date(2017, 1, 2)
        course.save()

        course_schedule.mon_start_time = datetime.time(2, 00, 0)
        course_schedule.save()

        self.client.get(reverse('planner_resource_courseschedules_events',
                                kwargs={'course_group': course_group.pk, 'course': course.pk}))

        # THEN
        self.assertEqual(_create_events_from_course_schedules_mock.call_count, 2)
