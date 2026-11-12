import datetime
import json
from urllib.parse import quote
from zoneinfo import ZoneInfo

from dateutil import parser
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.common.tests.helpers import commonhelper
from helium.common.utils import datetimeutils
from helium.planner.models import Homework, Reminder
from helium.planner.tests.helpers import attachmenthelper, coursegrouphelper, coursehelper, homeworkhelper, \
    categoryhelper, notehelper, occurrencehelper, resourcegrouphelper, resourcehelper, reminderhelper


class TestCaseHomeworkViews(APITestCase):
    def test_homework_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_homework_list')),
            self.client.get(reverse('planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_homework_clone',
                                     kwargs={'course_group': '9999', 'course': '9999', 'pk': '9999'}))
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def test_homework_carries_its_course_group_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(reverse('planner_homework_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['course'], course.pk)
        self.assertEqual(response.data[0]['course_group'], course_group.pk,
                         msg='a nested resource must carry its grandparent id so a client can '
                             'address it without resolving the parent first')

    def test_homework_course_group_is_read_only(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        other_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.patch(
            reverse('planner_coursegroups_courses_homework_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk}),
            json.dumps({'course_group': other_group.pk}),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course_group'], course_group.pk)

    def test_ordering_outside_allowlist_does_not_duplicate_rows(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        homework.resources.add(resourcehelper.given_resource_exists(resource_group))
        homework.resources.add(resourcehelper.given_resource_exists(resource_group))

        # WHEN
        response = self.client.get(reverse('planner_homework_list') + '?ordering=resources')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([homework_data['id'] for homework_data in response.data], [homework.pk])

    def test_get_homework(self):
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
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
        response1 = self.client.get(reverse('planner_homework_list'))
        response2 = self.client.get(
            reverse('planner_coursegroups_courses_homework_list',
                    kwargs={'course_group': course_group2.pk, 'course': course3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Homework.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_homework(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'priority': 12,
            'current_grade': '25/30',
            'completed': False,
            'category': category.pk,
            'resources': [resource.pk],
            'course': course.pk
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Homework.objects.count(), 1)
        homework = Homework.objects.get(pk=response.data['id'])
        homeworkhelper.verify_homework_matches_data(self, homework, data)
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_create_homework_with_resources_of_another_user_fails(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1', email='test1@email.com')
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                   email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user2)
        course = coursehelper.given_course_exists(course_group)
        other_resource_group = resourcegrouphelper.given_resource_group_exists(user1)
        other_resource = resourcehelper.given_resource_exists(other_resource_group)

        # WHEN
        data = {
            'title': 'some title',
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'current_grade': '-1/100',
            'resources': [other_resource.pk],
            'course': course.pk
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertIn(response.status_code, (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND))
        self.assertEqual(Homework.objects.count(), 0)

    def test_update_homework_course_without_matching_category_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        other_course = coursehelper.given_course_exists(course_group, title='Other Course')
        category = categoryhelper.given_category_exists(course)
        homework = homeworkhelper.given_homework_exists(course, category=category)

        # WHEN
        response = self.client.patch(
            reverse('planner_coursegroups_courses_homework_detail',
                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk}),
            json.dumps({'course': other_course.pk}), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('category', response.data)
        homework.refresh_from_db()
        self.assertEqual(homework.course_id, course.pk)

    def test_create_homework_without_category_lands_in_uncategorized(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2014-05-08T12:00:00Z',
            'end': '2014-05-08T14:00:00Z',
            'current_grade': '-1/100',
            'completed': False,
            'course': course.pk,
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        homework = Homework.objects.get(pk=response.data['id'])
        self.assertEqual(homework.category.title, 'Uncategorized')
        self.assertEqual(homework.category.course_id, course.pk)

    def test_clone_homework_copies_fields_resources_and_reminders(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category = coursehelper.given_course_with_category_exists(user)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)
        source = homeworkhelper.given_homework_exists(course, title='Quiz', category=category,
                                                     resources=[resource], current_grade='25/30',
                                                     completed=True)
        reminderhelper.given_reminder_exists(user, message='15 min before', offset=15,
                                             offset_type=enums.MINUTES, type=enums.PUSH, homework=source)
        reminderhelper.given_reminder_exists(user, message='1 hour before', offset=1,
                                             offset_type=enums.HOURS, type=enums.EMAIL, sent=True,
                                             homework=source)

        # WHEN
        response = self.client.post(reverse('planner_coursegroups_courses_homework_clone',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                    'pk': source.pk}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Homework.objects.count(), 2)
        self.assertEqual(Reminder.objects.count(), 4)

        clone = Homework.objects.get(pk=response.data['id'])
        self.assertNotEqual(clone.pk, source.pk)
        self.assertEqual(clone.title, 'Quiz 1')
        self.assertEqual(clone.start, source.start)
        self.assertEqual(clone.end, source.end)
        self.assertEqual(clone.priority, source.priority)
        self.assertEqual(clone.course_id, source.course_id)
        self.assertEqual(clone.category_id, source.category_id)
        self.assertEqual(list(clone.resources.values_list('pk', flat=True)), [resource.pk])

        self.assertEqual(clone.current_grade, '-1/100')
        self.assertFalse(clone.completed)
        self.assertIsNone(clone.completed_at)

        cloned_reminders = list(clone.reminders.order_by('message'))
        self.assertEqual(len(cloned_reminders), 2)

        fifteen = next(r for r in cloned_reminders if r.message == '15 min before')
        self.assertFalse(fifteen.sent)
        self.assertFalse(fifteen.dismissed)
        self.assertEqual(fifteen.user_id, user.pk)
        self.assertEqual(fifteen.start_of_range, clone.start - datetime.timedelta(minutes=15))

        one_hour = next(r for r in cloned_reminders if r.message == '1 hour before')
        self.assertFalse(one_hour.sent)
        self.assertEqual(one_hour.start_of_range, clone.start - datetime.timedelta(hours=1))

        source.refresh_from_db()
        self.assertEqual(source.title, 'Quiz')
        self.assertEqual(source.reminders.count(), 2)
        self.assertEqual(len(response.data['reminders']), 2)

    def test_clone_homework_increments_existing_trailing_number(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        source = homeworkhelper.given_homework_exists(course, title='Quiz 9')

        # WHEN
        response = self.client.post(reverse('planner_coursegroups_courses_homework_clone',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                    'pk': source.pk}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Quiz 10')

    def test_clone_homework_other_user_returns_404(self):
        # GIVEN
        owner = userhelper.given_a_user_exists()
        owner_course_group = coursegrouphelper.given_course_group_exists(owner)
        owner_course = coursehelper.given_course_exists(owner_course_group)
        owner_source = homeworkhelper.given_homework_exists(owner_course)
        reminderhelper.given_reminder_exists(owner, homework=owner_source)

        attacker = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                       email='test2@email.com')
        attacker_course_group = coursegrouphelper.given_course_group_exists(attacker)
        attacker_course = coursehelper.given_course_exists(attacker_course_group)

        # WHEN
        response = self.client.post(reverse('planner_coursegroups_courses_homework_clone',
                                            kwargs={'course_group': attacker_course_group.pk,
                                                    'course': attacker_course.pk, 'pk': owner_source.pk}),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Homework.objects.count(), 1)
        self.assertEqual(Reminder.objects.count(), 1)

    def test_create_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category = coursehelper.given_course_with_category_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08T12:00:00-0500',
            'end': '2014-05-08T14:00:00-0500',
            'priority': 50,
            'current_grade': '-1/100',
            'completed': False,
            'category': category.pk,
            'course': course.pk
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Homework.objects.count(), 1)
        homework = Homework.objects.get(pk=response.data['id'])
        self.assertEqual(homework.start.isoformat(), parser.parse(data['start']).astimezone(datetime.timezone.utc).isoformat())
        self.assertEqual(homework.end.isoformat(), parser.parse(data['end']).astimezone(datetime.timezone.utc).isoformat())

    def test_create_rejects_naive_datetime(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/New_York')
        course_group, course, category = coursehelper.given_course_with_category_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'all_day': False,
            'show_end_time': True,
            'start': '2014-05-08 12:00:00',
            'end': '2014-05-08 14:00:00',
            'priority': 50,
            'current_grade': '-1/100',
            'completed': False,
            'category': category.pk,
            'course': course.pk
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Homework.objects.count(), 0)
        self.assertIn('start', response.data)
        self.assertIn('timezone', str(response.data['start']))

    def test_get_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': homework.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_update_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category1 = coursehelper.given_course_with_category_exists(user)
        category2 = categoryhelper.given_category_exists(course, title='Test Category 2')
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource1 = resourcehelper.given_resource_exists(resource_group)
        resource2 = resourcehelper.given_resource_exists(resource_group)
        homework = homeworkhelper.given_homework_exists(course, category=category1, resources=[resource1])
        self.assertEqual(homework.title, '💻 Test Homework')

        # WHEN
        data = {
            'title': 'some title',
            'all_day': True,
            'show_end_time': False,
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-08T14:00:00Z',
            'priority': 12,
            'current_grade': '33/40',
            'completed': True,
            'category': category2.pk,
            'resources': [resource2.pk],
            'course': course.pk
        }
        response = self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                           kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                   'pk': homework.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        homework.refresh_from_db()
        homeworkhelper.verify_homework_matches_data(self, homework, response.data)

    def test_update_start_before_end_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00Z',
            'end': '2016-05-07T14:00:00Z',
        }
        response = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                             kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                     'pk': homework.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('must be before', response.data['non_field_errors'][0])

    def test_patch_converts_to_utc(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        data = {
            'start': '2016-05-08T12:00:00-0500',
            'end': '2016-05-08T14:00:00-0500',
        }
        response = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                             kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                     'pk': homework.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        homework.refresh_from_db()
        self.assertEqual(homework.start.isoformat(), parser.parse(data['start']).astimezone(datetime.timezone.utc).isoformat())
        self.assertEqual(homework.end.isoformat(), parser.parse(data['end']).astimezone(datetime.timezone.utc).isoformat())

    def test_patch_rejects_naive_datetime(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/New_York')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        original_start = homework.start

        # WHEN
        data = {
            'start': '2016-05-08 12:00:00',
            'end': '2016-05-08 14:00:00',
        }
        response = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                             kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                     'pk': homework.pk}),
                                     json.dumps(data),
                                     content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)
        homework.refresh_from_db()
        self.assertEqual(homework.start, original_start)

    def test_delete_homework_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': homework.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Homework.objects.filter(pk=homework.pk).exists())
        self.assertEqual(Homework.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        resourcegroup2 = resourcegrouphelper.given_resource_group_exists(user2)
        resource2 = resourcehelper.given_resource_exists(resourcegroup2)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        category2 = categoryhelper.given_category_exists(course2)
        homework = homeworkhelper.given_homework_exists(course1)

        # WHEN
        responses = [
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course2.pk}),
                             json.dumps({}),
                             content_type='application/json'),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course1.pk}),
                             json.dumps({'category': category2.pk}),
                             content_type='application/json'),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group1.pk, 'course': course1.pk}),
                             json.dumps({'resources': [resource2.pk]}),
                             content_type='application/json'),
            self.client.patch(
                reverse('planner_coursegroups_courses_homework_detail',
                        kwargs={'course_group': course_group1.pk, 'course': course1.pk, 'pk': homework.pk}),
                json.dumps({'course': course2.pk}),
                content_type='application/json'),
            self.client.patch(
                reverse('planner_coursegroups_courses_homework_detail',
                        kwargs={'course_group': course_group1.pk, 'course': course1.pk, 'pk': homework.pk}),
                json.dumps({'resources': [resource2.pk]}),
                content_type='application/json'),
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_404_NOT_FOUND)

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group.pk, 'course': course.pk})),
            self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk})),
            self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': course.pk, 'pk': homework.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': course_group.pk, 'course': course.pk,
                                               'pk': homework.pk}))
        ]

        # THEN
        self.assertTrue(Homework.objects.for_user(user1.pk).filter(pk=homework.pk).exists())
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
            'start': 'not-a-valid-date'
        }
        response = self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                            kwargs={'course_group': course_group.pk, 'course': course.pk}),
                                    json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_patch_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        data = {
            'start': 'not-a-valid-date'
        }
        response = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                             kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                     'pk': homework.pk}),
                                     json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('start', response.data)

    def test_update_invalid_fraction_fails(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response1 = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': homework.pk}),
                                      json.dumps({
                                          'current_grade': 'not-a-fraction'
                                      }),
                                      content_type='application/json')
        response2 = self.client.patch(reverse('planner_coursegroups_courses_homework_detail',
                                              kwargs={'course_group': course_group.pk, 'course': course.pk,
                                                      'pk': homework.pk}),
                                      json.dumps({
                                          'current_grade': 'invalid/4'
                                      }),
                                      content_type='application/json')

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('current_grade', response1.data)
        self.assertIn('current_grade', response2.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        responses = [
            self.client.get(reverse('planner_coursegroups_courses_homework_list',
                                    kwargs={'course_group': '9999', 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': course_group.pk, 'course': '9999'})),
            self.client.post(reverse('planner_coursegroups_courses_homework_list',
                                     kwargs={'course_group': '9999', 'course': course.pk})),
            self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': course_group.pk, 'course': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': course.pk, 'pk': '9999'})),
            self.client.get(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk})),
            self.client.put(reverse('planner_coursegroups_courses_homework_detail',
                                    kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk})),
            self.client.delete(reverse('planner_coursegroups_courses_homework_detail',
                                       kwargs={'course_group': '9999', 'course': '9999', 'pk': homework.pk}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('matches the given query', response.data['detail'].lower())

    def test_filter_id(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course, title='test1')
        homeworkhelper.given_homework_exists(course, title='test2')

        response = self.client.get(reverse('planner_homework_list') + f'?id={homework.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_range_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course,
                                             start=datetime.datetime(2017, 5, 8, 16, 0, 0,
                                                                     tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 5, 8, 16, 59, 0,
                                                                   tzinfo=datetime.timezone.utc))
        homework2 = homeworkhelper.given_homework_exists(course,
                                                         start=datetime.datetime(2017, 5, 8, 17, 0, 0,
                                                                                 tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 5, 8, 18, 0, 0,
                                                                               tzinfo=datetime.timezone.utc))
        homework4 = homeworkhelper.given_homework_exists(course,
                                                         start=datetime.datetime(2017, 5, 8, 19, 30, 0,
                                                                                 tzinfo=datetime.timezone.utc),
                                                         end=datetime.datetime(2017, 5, 8, 20, 0, 0,
                                                                               tzinfo=datetime.timezone.utc))
        homeworkhelper.given_homework_exists(course,
                                             start=datetime.datetime(2017, 5, 8, 20, 1, 0,
                                                                     tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 5, 8, 21, 0, 0,
                                                                   tzinfo=datetime.timezone.utc))

        response = self.client.get(
            reverse(
                'planner_homework_list') + f'?from={quote(homework2.start.isoformat())}&to={quote(homework4.end.isoformat())}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_range_query_multiday(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course,
                                             start=datetime.datetime(2025, 10, 31, 0, 0, 0,
                                                                     tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2025, 11, 3, 0, 0, 0,
                                                                   tzinfo=datetime.timezone.utc))

        response = self.client.get(
            reverse(
                'planner_homework_list') + f'?from=2025-11-01T00:00:00Z&to=2025-11-02T00:00:00Z')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_title_search_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course, title='test1')
        homeworkhelper.given_homework_exists(course, title='test2')

        response = self.client.get(reverse('planner_homework_list') + '?search=test1')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_search_query_folds_diacritics(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        match = homeworkhelper.given_homework_exists(course, title='Café reading')
        homeworkhelper.given_homework_exists(course, title='Other')

        # WHEN
        folded = self.client.get(reverse('planner_homework_list') + '?search=cafe')

        # THEN
        self.assertEqual([homework['id'] for homework in folded.data], [match.pk])

    def test_search_query_applies_within_date_range(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        in_range = homeworkhelper.given_homework_exists(course, title='Quiz', start=datetime.datetime(2017, 5, 8, 12, 0, tzinfo=datetime.timezone.utc),
                                                        end=datetime.datetime(2017, 5, 8, 14, 0, tzinfo=datetime.timezone.utc))
        homeworkhelper.given_homework_exists(course, title='Quiz', start=datetime.datetime(2017, 6, 8, 12, 0, tzinfo=datetime.timezone.utc),
                                             end=datetime.datetime(2017, 6, 8, 14, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(reverse('planner_homework_list') + '?search=quiz&from=2017-05-01&to=2017-05-31')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([homework['id'] for homework in response.data], [in_range.pk])

    def test_course_search_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group, title='testcourse')
        course2 = coursehelper.given_course_exists(course_group, title='othercourse')
        homework = homeworkhelper.given_homework_exists(course1, title='test1')
        homeworkhelper.given_homework_exists(course2, title='test2')

        response = self.client.get(reverse('planner_homework_list') + '?search=testcourse')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_filter_course_ids(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group, title='course1')
        course2 = coursehelper.given_course_exists(course_group, title='course2')
        course3 = coursehelper.given_course_exists(course_group, title='course3')
        homework1 = homeworkhelper.given_homework_exists(course1, title='test1')
        homework2 = homeworkhelper.given_homework_exists(course2, title='test2')
        homeworkhelper.given_homework_exists(course3, title='test3')

        response = self.client.get(reverse('planner_homework_list') + f'?course__id__in={course1.pk},{course2.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], homework1.title)
        self.assertEqual(response.data[1]['title'], homework2.title)

    def test_category_search_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category = coursehelper.given_course_with_category_exists(
            user, category_kwargs={'title': 'testcategory'})
        homework = homeworkhelper.given_homework_exists(course, title='test1', category=category)
        homeworkhelper.given_homework_exists(course, title='test2')

        response = self.client.get(reverse('planner_homework_list') + '?search=TesTCategorY')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], homework.title)

    def test_filter_category_ids(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category1 = coursehelper.given_course_with_category_exists(
            user, category_kwargs={'title': 'category1'})
        category2 = categoryhelper.given_category_exists(course, title='category2')
        category3 = categoryhelper.given_category_exists(course, title='category3')
        homework1 = homeworkhelper.given_homework_exists(course, title='test1', category=category1)
        homework2 = homeworkhelper.given_homework_exists(course, title='test2', category=category2)
        homeworkhelper.given_homework_exists(course, title='test3', category=category3)

        response = self.client.get(
            reverse('planner_homework_list') + f'?category__id__in={category1.pk},{category2.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], homework1.title)
        self.assertEqual(response.data[1]['title'], homework2.title)

    def test_filter_category_titles(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group, course, category1 = coursehelper.given_course_with_category_exists(
            user, category_kwargs={'title': 'category,1'})
        category2 = categoryhelper.given_category_exists(course, title='category,2')
        category3 = categoryhelper.given_category_exists(course, title='category,3')
        homework1 = homeworkhelper.given_homework_exists(course, title='test1', category=category1)
        homework2 = homeworkhelper.given_homework_exists(course, title='test2', category=category2)
        homeworkhelper.given_homework_exists(course, title='test3', category=category3)

        response = self.client.get(
            reverse(
                'planner_homework_list')
            + f'?category__title__in=%27{quote(category1.title)}%27,%27{quote(category2.title)}%27')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], homework1.title)
        self.assertEqual(response.data[1]['title'], homework2.title)

    def test_filter_hidden_course_group(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=False)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course)

        response = self.client.get(reverse('planner_homework_list') + '?shown_on_calendar=true')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

    def test_filter_overdue(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user, shown_on_calendar=False)
        course = coursehelper.given_course_exists(course_group)
        homeworkhelper.given_homework_exists(course,
                                             title="overdue",
                                             completed=False,
                                             start=timezone.now() - datetime.timedelta(seconds=1))
        homeworkhelper.given_homework_exists(course,
                                             title="not overdue",
                                             completed=True,
                                             start=timezone.now() - datetime.timedelta(seconds=1))
        homeworkhelper.given_homework_exists(course,
                                             title="not overdue",
                                             completed=False,
                                             start=timezone.now() + datetime.timedelta(minutes=1))

        response = self.client.get(reverse('planner_homework_list') + '?overdue=true')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual("overdue", response.data[0]['title'])

        response = self.client.get(reverse('planner_homework_list') + '?overdue=false')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        for h in response.data:
            self.assertEqual("not overdue", h['title'])

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework1 = homeworkhelper.given_homework_exists(course)
        homework2 = homeworkhelper.given_homework_exists(course)
        homework3 = homeworkhelper.given_homework_exists(course)

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Homework.objects.filter(pk=homework1.pk).update(updated_at=old_time)
        Homework.objects.filter(pk=homework2.pk).update(updated_at=recent_time)
        Homework.objects.filter(pk=homework3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_homework_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(homework2.pk, returned_ids)
        self.assertIn(homework3.pk, returned_ids)
        self.assertNotIn(homework1.pk, returned_ids)

    def test_range_query_date_only_from_boundary_edges(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/Chicago')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # Item 1 minute BEFORE from boundary: Feb 2 05:59 UTC = Feb 1 11:59pm Chicago
        homework_before_from = homeworkhelper.given_homework_exists(
            course,
            title='before_from',
            start=datetime.datetime(2026, 2, 2, 5, 59, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 5, 59, 30, tzinfo=datetime.timezone.utc))

        # Item exactly AT from boundary: Feb 2 06:00 UTC = Feb 2 00:00 Chicago
        homework_at_from = homeworkhelper.given_homework_exists(
            course,
            title='at_from',
            start=datetime.datetime(2026, 2, 2, 6, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # Item 1 minute AFTER from boundary: Feb 2 06:01 UTC = Feb 2 00:01 Chicago
        homework_after_from = homeworkhelper.given_homework_exists(
            course,
            title='after_from',
            start=datetime.datetime(2026, 2, 2, 6, 1, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(
            reverse('planner_homework_list') + '?from=2026-02-02&to=2026-02-03')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        titles = {item['title'] for item in response.data}
        self.assertNotIn('before_from', titles)
        self.assertIn('at_from', titles)
        self.assertIn('after_from', titles)

    def test_range_query_date_only_to_boundary_edges(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/Chicago')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # Item 1 minute BEFORE to boundary: Feb 3 05:59 UTC = Feb 2 11:59pm Chicago
        homework_before_to = homeworkhelper.given_homework_exists(
            course,
            title='before_to',
            start=datetime.datetime(2026, 2, 3, 5, 59, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 3, 5, 59, 30, tzinfo=datetime.timezone.utc))

        # Item exactly AT to boundary: Feb 3 06:00 UTC = Feb 3 00:00 Chicago
        homework_at_to = homeworkhelper.given_homework_exists(
            course,
            title='at_to',
            start=datetime.datetime(2026, 2, 3, 6, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 3, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # Item 1 minute AFTER to boundary: Feb 3 06:01 UTC = Feb 3 00:01 Chicago
        homework_after_to = homeworkhelper.given_homework_exists(
            course,
            title='after_to',
            start=datetime.datetime(2026, 2, 3, 6, 1, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 3, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(
            reverse('planner_homework_list') + '?from=2026-02-01&to=2026-02-03')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        titles = {item['title'] for item in response.data}
        self.assertIn('before_to', titles)
        self.assertIn('at_to', titles)
        self.assertNotIn('after_to', titles)

    def test_range_query_date_only_both_boundaries(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='America/Chicago')
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # BEFORE from: Feb 2 05:00 UTC = Feb 1 11pm Chicago
        homeworkhelper.given_homework_exists(
            course, title='1_before_from',
            start=datetime.datetime(2026, 2, 2, 5, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 5, 30, 0, tzinfo=datetime.timezone.utc))

        # AT from: Feb 2 06:00 UTC = Feb 2 midnight Chicago
        homeworkhelper.given_homework_exists(
            course, title='2_at_from',
            start=datetime.datetime(2026, 2, 2, 6, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # MIDDLE: Feb 2 18:00 UTC = Feb 2 noon Chicago
        homeworkhelper.given_homework_exists(
            course, title='3_middle',
            start=datetime.datetime(2026, 2, 2, 18, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 2, 19, 0, 0, tzinfo=datetime.timezone.utc))

        # AT to: Feb 3 06:00 UTC = Feb 3 midnight Chicago
        homeworkhelper.given_homework_exists(
            course, title='4_at_to',
            start=datetime.datetime(2026, 2, 3, 6, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 3, 6, 30, 0, tzinfo=datetime.timezone.utc))

        # AFTER to: Feb 3 07:00 UTC = Feb 3 1am Chicago
        homeworkhelper.given_homework_exists(
            course, title='5_after_to',
            start=datetime.datetime(2026, 2, 3, 7, 0, 0, tzinfo=datetime.timezone.utc),
            end=datetime.datetime(2026, 2, 3, 7, 30, 0, tzinfo=datetime.timezone.utc))

        # WHEN
        response = self.client.get(
            reverse('planner_homework_list') + '?from=2026-02-02&to=2026-02-03')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        titles = {item['title'] for item in response.data}
        self.assertNotIn('1_before_from', titles)
        self.assertIn('2_at_from', titles)
        self.assertIn('3_middle', titles)
        self.assertIn('4_at_to', titles)
        self.assertNotIn('5_after_to', titles)

    def test_filter_id_cannot_access_other_users_data(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        course_group = coursegrouphelper.given_course_group_exists(user1)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)

        # WHEN
        response = self.client.get(reverse('planner_homework_list') + f'?id={homework.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)


class TestCaseHomeworkOccurrenceViews(APITestCase):
    def test_create_open_ended_repeating_homework_ends_at_the_class_last_day_in_the_user_zone(self):
        cases = (
            ('Europe/Amsterdam', datetime.datetime(2030, 5, 7, 0, 30), 'FREQ=WEEKLY;BYDAY=TU',
             'FREQ=WEEKLY;BYDAY=TU;UNTIL=20300603T215959Z', [datetime.date(2030, 5, day) for day in (7, 14, 21, 28)]),
            ('America/Los_Angeles', datetime.datetime(2030, 5, 6, 23, 0), 'FREQ=WEEKLY;BYDAY=MO',
             'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300604T065959Z',
             [*(datetime.date(2030, 5, day) for day in (6, 13, 20, 27)), datetime.date(2030, 6, 3)]),
        )
        for index, (zone, local_start, rule, expected_rule, expected_dates) in enumerate(cases):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
                course_group, course, category = _given_course(user)
                start = local_start.replace(tzinfo=tz)

                # WHEN
                response = _post(self.client, course_group, course, {
                    **_homework_data(course, category, start), 'recurrence_rule': rule})

                # THEN
                self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
                self.assertEqual(Homework.objects.filter(course=course).count(), 1)
                homework = Homework.objects.get(pk=response.data['id'])
                self.assertEqual(homework.recurrence_rule, expected_rule)
                self.assertEqual(response.data['recurrence_rule'], expected_rule)
                self.assertEqual([occurrence_start.astimezone(tz).date() for occurrence_start, _ in homework.occurrences()],
                                 expected_dates)

    def test_create_repeating_homework_beyond_the_occurrence_cap_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user, end_date=datetime.date(2032, 1, 1))
        start = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=ZoneInfo('Europe/Amsterdam'))

        # WHEN
        response = _post(self.client, course_group, course, {
            **_homework_data(course, category, start), 'recurrence_rule': 'FREQ=DAILY'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['recurrence_rule'], 'It repeats more than 366 times.')
        self.assertFalse(Homework.objects.exists())

    def test_create_repeating_homework_with_no_dates_by_the_class_last_day_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        start = datetime.datetime(2030, 6, 10, 9, 0, tzinfo=ZoneInfo('Europe/Amsterdam'))

        # WHEN
        response = _post(self.client, course_group, course, {
            **_homework_data(course, category, start), 'recurrence_rule': 'FREQ=WEEKLY;BYDAY=MO'})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['recurrence_rule'], "It has no dates by the class's last day.")
        self.assertFalse(Homework.objects.exists())

    def test_create_repeating_homework_completed_or_graded_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        start = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=ZoneInfo('Europe/Amsterdam'))
        cases = ({'completed': True}, {'current_grade': '90/100'})

        for overrides in cases:
            with self.subTest(overrides=overrides):
                # WHEN
                response = _post(self.client, course_group, course, {
                    **_homework_data(course, category, start), 'recurrence_rule': 'FREQ=WEEKLY;BYDAY=MO',
                    **overrides})

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("A repeating Homework isn't completed or graded itself", str(response.data))
                self.assertFalse(Homework.objects.exists())

    def test_patch_all_completing_or_grading_a_repeating_homework_returns_400(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        cases = ({'completed': True}, {'current_grade': '90/100'})

        for body in cases:
            with self.subTest(body=body):
                # WHEN
                response = _patch(self.client, series, body, 'scope=all')

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("A repeating Homework isn't completed or graded itself", str(response.data))
                series.refresh_from_db()
                self.assertFalse(series.completed)
                self.assertEqual(series.current_grade, '-1/100')
                self.assertIsNone(series.exception_dates)
                self.assertEqual(Homework.objects.count(), 1)

    def test_patch_this_occurrence_completes_and_grades_it_as_its_own_homework(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        resource = resourcehelper.given_resource_exists(resourcegrouphelper.given_resource_group_exists(user))
        series = _given_weekly_series(course, category, resources=[resource])
        reminderhelper.given_reminder_exists(user, homework=series, offset=30, message='Quiz soon')
        occurrence = datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz)

        # WHEN
        response = _patch(self.client, series, {'completed': True, 'current_grade': '90/100'},
                          occurrencehelper.occurrence_query(occurrence))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        detached = Homework.objects.get(pk=response.data['id'])
        self.assertNotEqual(detached.pk, series.pk)
        self.assertEqual(detached.title, 'Weekly quiz')
        self.assertEqual(detached.start, occurrence)
        self.assertEqual(detached.end, occurrence + datetime.timedelta(hours=1))
        self.assertIsNone(detached.recurrence_rule)
        self.assertTrue(detached.completed)
        self.assertEqual(detached.current_grade, '90/100')
        self.assertEqual(detached.course_id, course.pk)
        self.assertEqual(detached.category_id, category.pk)
        self.assertEqual(list(detached.resources.values_list('pk', flat=True)), [resource.pk])
        reminder = detached.reminders.get()
        self.assertEqual((reminder.message, reminder.offset, reminder.sent), ('Quiz soon', 30, False))
        self.assertEqual(reminder.start_of_range, occurrence - datetime.timedelta(minutes=30))
        series.refresh_from_db()
        self.assertEqual(series.exception_dates, [datetimeutils.as_utc_iso(occurrence)])
        self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z')
        self.assertEqual(series.start, datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz))
        self.assertFalse(series.completed)
        self.assertEqual(series.current_grade, '-1/100')
        self.assertEqual(series.title, 'Weekly quiz')
        course.refresh_from_db()
        category.refresh_from_db()
        self.assertEqual(float(category.average_grade), 90.0)
        self.assertEqual(float(course.current_grade), 90.0)

    def test_patch_this_last_remaining_occurrence_hands_note_and_attachments_over(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        first = datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz)
        series = _given_weekly_series(course, category, rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2',
                                      exception_dates=[datetimeutils.as_utc_iso(first)])
        attachment = attachmenthelper.given_attachment_exists(user, homework=series)
        note = notehelper.given_note_linked_to_homework(user, series)
        last = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)

        # WHEN
        response = _patch(self.client, series, {'completed': True}, occurrencehelper.occurrence_query(last))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertFalse(Homework.objects.filter(pk=series.pk).exists())
        detached = Homework.objects.get(pk=response.data['id'])
        self.assertEqual(detached.start, last)
        self.assertTrue(detached.completed)
        self.assertEqual(list(note.homework.all()), [detached])
        attachment.refresh_from_db()
        self.assertEqual(attachment.homework_id, detached.pk)

    def test_patch_this_with_a_recurrence_change_returns_400(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        occurrence = datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz)
        cases = ({'recurrence_rule': 'FREQ=WEEKLY;BYDAY=TU'}, {'exception_dates': []})

        for body in cases:
            with self.subTest(body=body):
                # WHEN
                response = _patch(self.client, series, body, occurrencehelper.occurrence_query(occurrence))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertEqual(response.data['scope'], 'A repeat changes with `scope=all`.')
                self.assertEqual(Homework.objects.count(), 1)
                series.refresh_from_db()
                self.assertIsNone(series.exception_dates)
                self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z')

    def test_patch_from_an_occurrence_moves_the_whole_series(self):
        cases = (
            ('Europe/Amsterdam', 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z',
             'FREQ=WEEKLY;BYDAY=TU;UNTIL=20300604T232959Z'),
            ('America/Los_Angeles', 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300604T065959Z',
             'FREQ=WEEKLY;BYDAY=TU;UNTIL=20300605T082959Z'),
        )
        for index, (zone, rule, expected_rule) in enumerate(cases):
            with self.subTest(zone=zone):
                # GIVEN
                tz = ZoneInfo(zone)
                user = userhelper.given_a_user_exists_and_is_authenticated(
                    self.client, username=f'user{index}', email=f'user{index}@test.com', time_zone=zone)
                course_group, course, category = _given_course(user)
                series = _given_weekly_series(
                    course, category, rule=rule, start=datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz),
                    exception_dates=[datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 27, 9, 0, tzinfo=tz))])
                occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
                moved = datetime.datetime(2030, 5, 14, 10, 30, tzinfo=tz)

                # WHEN
                response = _patch(self.client, series, {'start': moved.isoformat(),
                                                        'end': (moved + datetime.timedelta(hours=2)).isoformat()},
                                  occurrencehelper.occurrence_query(occurrence, scope=None))

                # THEN
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertEqual(response.data['id'], series.pk)
                series.refresh_from_db()
                self.assertEqual(series.start, datetime.datetime(2030, 5, 7, 10, 30, tzinfo=tz))
                self.assertEqual(series.end - series.start, datetime.timedelta(hours=2))
                self.assertEqual(series.recurrence_rule, expected_rule)
                self.assertEqual(series.exception_dates,
                                 [datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 28, 10, 30, tzinfo=tz))])
                self.assertEqual([start.astimezone(tz).date() for start, _ in series.occurrences()],
                                 [datetime.date(2030, 5, 7), datetime.date(2030, 5, 14), datetime.date(2030, 5, 21),
                                  datetime.date(2030, 6, 4)])
                self.assertEqual(Homework.objects.filter(course=course).count(), 1)

    def test_delete_this_occurrence_leaves_it_out_of_the_series(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)

        # WHEN
        response = _delete(self.client, series, occurrencehelper.occurrence_query(occurrence))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        series.refresh_from_db()
        self.assertEqual(series.exception_dates, [datetimeutils.as_utc_iso(occurrence)])
        self.assertEqual(series.recurrence_rule, 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z')
        self.assertEqual(len(list(series.occurrences())), 4)

    def test_delete_this_last_remaining_occurrence_deletes_the_series(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(
            course, category, rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2',
            exception_dates=[datetimeutils.as_utc_iso(datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz))])

        # WHEN
        response = _delete(self.client, series, occurrencehelper.occurrence_query('2030-05-13T07:00:00Z'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Homework.objects.filter(pk=series.pk).exists())

    def test_delete_all_deletes_the_series_but_keeps_broken_out_homework(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        occurrence = datetime.datetime(2030, 5, 13, 9, 0, tzinfo=tz)
        detached_id = _patch(self.client, series, {'completed': True},
                             occurrencehelper.occurrence_query(occurrence)).data['id']

        # WHEN
        response = _delete(self.client, series, 'scope=all')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Homework.objects.filter(pk=series.pk).exists())
        self.assertEqual(list(Homework.objects.values_list('pk', 'start', 'completed')),
                         [(detached_id, occurrence, True)])

    def test_range_query_includes_a_series_that_started_before_the_window(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        homeworkhelper.given_homework_exists(course, title='Before the window',
                                             start=datetime.datetime(2030, 5, 6, 9, 0, tzinfo=tz),
                                             end=datetime.datetime(2030, 5, 6, 10, 0, tzinfo=tz))
        homeworkhelper.given_homework_exists(course, title='Series after the window',
                                             start=datetime.datetime(2030, 6, 3, 9, 0, tzinfo=tz),
                                             end=datetime.datetime(2030, 6, 3, 10, 0, tzinfo=tz),
                                             recurrence_rule='FREQ=WEEKLY;BYDAY=MO;COUNT=2')

        # WHEN
        response = self.client.get(reverse('planner_homework_list') +
                                   f"?from={quote('2030-05-20T00:00:00Z')}&to={quote('2030-05-21T00:00:00Z')}")

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([(item['id'], item['recurrence_rule']) for item in response.data],
                         [(series.pk, 'FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z')])

    def test_clone_repeating_homework_at_an_occurrence_returns_a_single_homework_there(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)
        occurrence = datetime.datetime(2030, 5, 20, 9, 0, tzinfo=tz)

        # WHEN
        response = _clone(self.client, series, occurrence)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        clone = Homework.objects.get(pk=response.data['id'])
        self.assertEqual(clone.title, 'Weekly quiz 1')
        self.assertIsNone(clone.recurrence_rule)
        self.assertIsNone(clone.exception_dates)
        self.assertEqual(clone.start, occurrence)
        self.assertEqual(clone.end, occurrence + datetime.timedelta(hours=1))
        self.assertEqual(clone.category_id, category.pk)
        series.refresh_from_db()
        self.assertIsNone(series.exception_dates)

    def test_clone_repeating_homework_at_a_non_occurrence_returns_400(self):
        # GIVEN
        tz = ZoneInfo('Europe/Amsterdam')
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client, time_zone='Europe/Amsterdam')
        course_group, course, category = _given_course(user)
        series = _given_weekly_series(course, category)

        # WHEN
        response = _clone(self.client, series, datetime.datetime(2030, 5, 21, 9, 0, tzinfo=tz))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['occurrence_start'], 'Not an occurrence of this assignment.')
        self.assertEqual(Homework.objects.count(), 1)


def _given_course(user, end_date=datetime.date(2030, 6, 3)):
    return coursehelper.given_course_with_category_exists(
        user, course_group_kwargs={'start_date': datetime.date(2030, 5, 1), 'end_date': end_date},
        course_kwargs={'start_date': datetime.date(2030, 5, 1), 'end_date': end_date})


def _given_weekly_series(course, category, rule='FREQ=WEEKLY;BYDAY=MO;UNTIL=20300603T215959Z', start=None,
                         exception_dates=None, resources=None):
    return homeworkhelper.given_weekly_homework_exists(
        course, title='Weekly quiz', category=category,
        start=start or datetime.datetime(2030, 5, 6, 9, 0, tzinfo=ZoneInfo('Europe/Amsterdam')),
        recurrence_rule=rule, exception_dates=exception_dates, resources=resources)


def _homework_data(course, category, start):
    return {
        'title': 'Weekly quiz',
        'all_day': False,
        'show_end_time': False,
        'start': start.isoformat(),
        'end': (start + datetime.timedelta(hours=1)).isoformat(),
        'priority': 50,
        'current_grade': '-1/100',
        'completed': False,
        'category': category.pk,
        'course': course.pk,
    }


def _post(client, course_group, course, data):
    return client.post(reverse('planner_coursegroups_courses_homework_list',
                               kwargs={'course_group': course_group.pk, 'course': course.pk}),
                       json.dumps(data), content_type='application/json')


def _detail_url(homework):
    return reverse('planner_coursegroups_courses_homework_detail',
                   kwargs={'course_group': homework.course.course_group_id, 'course': homework.course_id,
                           'pk': homework.pk})


def _patch(client, homework, data, query):
    return client.patch(f'{_detail_url(homework)}?{query}', json.dumps(data), content_type='application/json')


def _delete(client, homework, query):
    return client.delete(f'{_detail_url(homework)}?{query}')


def _clone(client, homework, occurrence_start):
    return client.post(reverse('planner_coursegroups_courses_homework_clone',
                               kwargs={'course_group': homework.course.course_group_id,
                                       'course': homework.course_id, 'pk': homework.pk}) +
                       f'?{occurrencehelper.occurrence_query(occurrence_start, scope=None)}')
