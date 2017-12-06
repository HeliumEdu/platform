"""
Tests for CourseGroup interaction.
"""
import datetime
import json
import uuid

from dateutil import parser
from django.test import TestCase
from django.urls import reverse

from helium.auth.tests.helpers import userhelper
from helium.planner.models import CourseGroup
from helium.planner.tests.helpers import coursegrouphelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseCourseGroup(TestCase):
    def test_coursegroup_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        response1 = self.client.get(reverse('api_planner_coursegroup_list'))
        response2 = self.client.get(reverse('api_planner_coursegroup_detail', kwargs={'pk': 1}))

        # THEN
        self.assertEqual(response1.status_code, 302)
        self.assertRedirects(response1, '/login?next={}'.format(reverse('api_planner_coursegroup_list')))
        self.assertEqual(response2.status_code, 302)
        self.assertRedirects(response2,
                             '/login?next={}'.format(reverse('api_planner_coursegroup_detail', kwargs={'pk': 1})))

    def test_get_coursegroups(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        coursegrouphelper.given_course_group_exists(user1)
        coursegrouphelper.given_course_group_exists(user2)
        coursegrouphelper.given_course_group_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroup_list'))

        # THEN
        self.assertEqual(len(response.data), 2)

    def test_post_coursegroup(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'start_date': '2015-03-05',
            'end_date': '2015-07-09',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('api_planner_coursegroup_list'), json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, 201)
        self.assertEqual(CourseGroup.objects.count(), 1)
        course_group = CourseGroup.objects.get(pk=response.data['id'])
        self.assertEqual(course_group.title, 'some title')
        self.assertEqual(course_group.start_date, datetime.date(2015, 3, 5))
        self.assertEqual(course_group.end_date, datetime.date(2015, 7, 9))
        self.assertEqual(course_group.shown_on_calendar, False)
        self.assertEqual(course_group.user.pk, user.pk)

    def test_get_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course_group.average_grade = 87.66
        course_group.trend = 0.65
        course_group.save()
        coursegrouphelper.given_course_group_exists(user, 'test2')

        # WHEN
        response = self.client.get(reverse('api_planner_coursegroup_detail', kwargs={'pk': course_group.pk}))

        # THEN
        self.assertEqual(course_group.title, response.data['title'])
        self.assertEqual(course_group.start_date, parser.parse(response.data['start_date']).date())
        self.assertEqual(course_group.end_date, parser.parse(response.data['end_date']).date())
        self.assertEqual(course_group.shown_on_calendar, response.data['shown_on_calendar'])
        self.assertEqual(course_group.average_grade, float(response.data['average_grade']))
        self.assertEqual(course_group.trend, response.data['trend'])
        self.assertEqual(course_group.user.pk, response.data['user'])

    def test_put_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        self.assertEqual(course_group.title, 'Test Course Group')
        self.assertTrue(course_group.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False,
            # Intentionally NOT changing this value
            'start_date': course_group.start_date.isoformat(),
            'end_date': course_group.end_date.isoformat()
        }
        response = self.client.put(reverse('api_planner_coursegroup_detail', kwargs={'pk': course_group.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.data['title'], 'new title')
        self.assertFalse(response.data['shown_on_calendar'])
        course_group = CourseGroup.objects.get(pk=course_group.pk)
        self.assertEqual(course_group.title, response.data['title'])
        self.assertFalse(course_group.shown_on_calendar, response.data['shown_on_calendar'])

    def test_delete_coursegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        coursegrouphelper.given_course_group_exists(user)

        # WHEN
        self.client.delete(reverse('api_planner_coursegroup_detail', kwargs={'pk': course_group.pk}))

        # THEN
        self.assertFalse(CourseGroup.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(CourseGroup.objects.count(), 1)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)

        # WHEN
        response = self.client.delete(reverse('api_planner_coursegroup_detail', kwargs={'pk': course_group.pk}))

        # THEN
        self.assertEqual(response.status_code, 404)
        self.assertTrue(CourseGroup.objects.filter(pk=course_group.pk).exists())
        self.assertEqual(CourseGroup.objects.count(), 1)

    def test_put_read_only_field_does_nothing(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        private_slug = str(uuid.uuid4())
        course_group.private_slug = private_slug
        course_group.save()

        # WHEN
        data = {
            'private_slug': 'new_slug'
        }
        response = self.client.put(reverse('api_user_settings'), json.dumps(data), content_type='application/json')

        # THEN
        course_group = CourseGroup.objects.get(id=user.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(course_group.private_slug, private_slug)
