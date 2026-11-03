import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Resource
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, resourcegrouphelper, resourcehelper


class TestCaseResourceViews(APITestCase):
    def test_resource_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_resources_list')),
            self.client.get(reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': '9999'})),
            self.client.post(
                reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': '9999'})),
            self.client.get(
                reverse('planner_resourcegroups_resources_detail',
                        kwargs={'resource_group': '9999', 'pk': '9999'})),
            self.client.put(
                reverse('planner_resourcegroups_resources_detail',
                        kwargs={'resource_group': '9999', 'pk': '9999'})),
            self.client.delete(
                reverse('planner_resourcegroups_resources_detail',
                        kwargs={'resource_group': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_resources(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user1)
        resource_group2 = resourcegrouphelper.given_resource_group_exists(user2)
        resource_group3 = resourcegrouphelper.given_resource_group_exists(user2)
        resourcehelper.given_resource_exists(resource_group1)
        resourcehelper.given_resource_exists(resource_group2)
        resourcehelper.given_resource_exists(resource_group3)
        resourcehelper.given_resource_exists(resource_group3)

        # WHEN
        response1 = self.client.get(reverse('planner_resources_list'))
        response2 = self.client.get(
            reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': resource_group3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Resource.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_resource(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
            'website': 'http://www.some-material.com',
            'price': '500.27',
            'resource_group': resource_group.pk,
            'courses': [course.pk]
        }
        response = self.client.post(
            reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': resource_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Resource.objects.count(), 1)
        resource = Resource.objects.get(pk=response.data['id'])
        resourcehelper.verify_resource_matches_data(self, resource, response.data)

    def test_update_resource_without_group_keeps_group(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        data = {
            'title': 'renamed',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
        }
        response = self.client.put(
            reverse('planner_resourcegroups_resources_detail',
                    kwargs={'resource_group': resource_group.pk, 'pk': resource.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'renamed')
        self.assertEqual(response.data['resource_group'], resource_group.pk)

    def test_get_resource_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        response = self.client.get(reverse('planner_resourcegroups_resources_detail',
                                           kwargs={'resource_group': resource_group.pk, 'pk': resource.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resourcehelper.verify_resource_matches_data(self, resource, response.data)

    def test_update_resource_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group1, courses=[course1])
        self.assertEqual(resource.title, '📘 Test Material')

        # WHEN
        data = {
            'title': 'some title',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
            'website': 'http://www.some-material.com',
            'price': '500.27',
            'courses': [course2.pk],
            'resource_group': resource_group1.pk
        }
        response = self.client.put(
            reverse('planner_resourcegroups_resources_detail',
                    kwargs={'resource_group': resource_group1.pk, 'pk': resource.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        resource.refresh_from_db()
        resourcehelper.verify_resource_matches_data(self, resource, response.data)

    def test_update_multiple_courses(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group1)

        # WHEN
        data = {
            'courses': [course1.pk, course2.pk],
            # Intentionally NOT changing these value
            'title': resource.title,
            'resource_group': resource.resource_group.pk
        }
        response = self.client.put(
            reverse('planner_resourcegroups_resources_detail',
                    kwargs={'resource_group': resource_group1.pk, 'pk': resource.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['courses'], data['courses'])
        resource.refresh_from_db()
        resourcehelper.verify_resource_matches_data(self, resource, response.data)

    def test_update_resource_group(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user)
        resource_group2 = resourcegrouphelper.given_resource_group_exists(user, title='📚 Another Material Group')
        resource = resourcehelper.given_resource_exists(resource_group1)
        self.assertEqual(resource.resource_group_id, resource_group1.pk)

        # WHEN
        data = {
            'title': resource.title,
            'status': resource.status,
            'condition': resource.condition,
            'website': resource.website,
            'price': resource.price,
            'courses': [],
            'resource_group': resource_group2.pk,
        }
        response = self.client.put(
            reverse('planner_resourcegroups_resources_detail',
                    kwargs={'resource_group': resource_group1.pk, 'pk': resource.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resource.refresh_from_db()
        resourcehelper.verify_resource_matches_data(self, resource, response.data)
        self.assertEqual(resource.resource_group_id, resource_group2.pk)

    def test_delete_resource_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        response = self.client.delete(reverse('planner_resourcegroups_resources_detail',
                                              kwargs={'resource_group': resource_group.pk, 'pk': resource.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Resource.objects.filter(pk=resource_group.pk).exists())
        self.assertEqual(Resource.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user1)
        resource_group2 = resourcegrouphelper.given_resource_group_exists(user2)
        resource = resourcehelper.given_resource_exists(resource_group1, courses=[course1])

        # WHEN
        forbidden_responses = [
            self.client.post(
                reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': resource_group1.pk}),
                json.dumps({'courses': [course2.pk]}),
                content_type='application/json'),
            self.client.post(
                reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': resource_group2.pk}),
                json.dumps({}),
                content_type='application/json'),
            self.client.put(
                reverse('planner_resourcegroups_resources_detail',
                        kwargs={'resource_group': resource_group1.pk, 'pk': resource.pk}),
                json.dumps({'courses': [course2.pk]}),
                content_type='application/json')
        ]
        move_attempt = self.client.put(
            reverse('planner_resourcegroups_resources_detail',
                    kwargs={'resource_group': resource_group1.pk, 'pk': resource.pk}),
            json.dumps({
                'title': resource.title,
                'status': resource.status,
                'condition': resource.condition,
                'website': resource.website,
                'price': resource.price,
                'courses': [course1.pk],
                'resource_group': resource_group2.pk,
            }),
            content_type='application/json')

        # THEN
        for response in forbidden_responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(move_attempt.status_code, status.HTTP_404_NOT_FOUND)
        resource.refresh_from_db()
        self.assertEqual(resource.resource_group_id, resource_group1.pk)

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        resource_group = resourcegrouphelper.given_resource_group_exists(user1)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        responses = [
            self.client.get(reverse('planner_resourcegroups_resources_list',
                                    kwargs={'resource_group': resource_group.pk})),
            self.client.post(reverse('planner_resourcegroups_resources_list',
                                     kwargs={'resource_group': resource_group.pk}),
                             content_type='application/json'),
            self.client.get(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': resource_group.pk, 'pk': resource.pk})),
            self.client.put(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': resource_group.pk, 'pk': resource.pk})),
            self.client.delete(reverse('planner_resourcegroups_resources_detail',
                                       kwargs={'resource_group': resource_group.pk, 'pk': resource.pk}))
        ]

        # THEN
        self.assertTrue(Resource.objects.filter(pk=resource.pk, resource_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)

        # WHEN
        data = {
            'status': 'not-a-valid-status'
        }
        response = self.client.post(
            reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': resource_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        self.assertEqual(Resource.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        data = {
            'status': 'not-a-valid-status'
        }
        response = self.client.put(reverse('planner_resourcegroups_resources_detail',
                                           kwargs={'resource_group': resource_group.pk, 'pk': resource.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group)

        responses = [
            self.client.get(reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': '9999'})),
            self.client.post(
                reverse('planner_resourcegroups_resources_list', kwargs={'resource_group': '9999'}),
                content_type='application/json'),
            self.client.get(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_resourcegroups_resources_detail',
                                       kwargs={'resource_group': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': resource_group.pk, 'pk': '9999'})),
            self.client.put(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': resource_group.pk, 'pk': '9999'})),
            self.client.delete(reverse('planner_resourcegroups_resources_detail',
                                       kwargs={'resource_group': resource_group.pk, 'pk': '9999'})),
            self.client.get(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': '9999', 'pk': resource.pk})),
            self.client.put(reverse('planner_resourcegroups_resources_detail',
                                    kwargs={'resource_group': '9999', 'pk': resource.pk})),
            self.client.delete(reverse('planner_resourcegroups_resources_detail',
                                       kwargs={'resource_group': '9999', 'pk': resource.pk}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('matches the given query', response.data['detail'].lower())

    def test_courses_filter_query(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        coursehelper.given_course_exists(course_group)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource = resourcehelper.given_resource_exists(resource_group, courses=[course1, course2])

        response = self.client.get(
            reverse('planner_resources_list') + f'?courses={course1.pk}&courses={course2.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], resource.title)

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        resource1 = resourcehelper.given_resource_exists(resource_group)
        resource2 = resourcehelper.given_resource_exists(resource_group, title='Material 2')
        resource3 = resourcehelper.given_resource_exists(resource_group, title='Material 3')

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Resource.objects.filter(pk=resource1.pk).update(updated_at=old_time)
        Resource.objects.filter(pk=resource2.pk).update(updated_at=recent_time)
        Resource.objects.filter(pk=resource3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_resources_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(resource2.pk, returned_ids)
        self.assertIn(resource3.pk, returned_ids)
        self.assertNotIn(resource1.pk, returned_ids)

    def test_filter_id_cannot_access_other_users_data(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        resource_group = resourcegrouphelper.given_resource_group_exists(user1)
        resource = resourcehelper.given_resource_exists(resource_group)

        # WHEN
        response = self.client.get(reverse('planner_resources_list') + f'?id={resource.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
