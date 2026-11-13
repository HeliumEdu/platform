import datetime
import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common.tests.helpers import commonhelper
from helium.planner.models import ResourceGroup
from helium.planner.tests.helpers import resourcegrouphelper


class TestCaseResourceGroupViews(APITestCase):
    def test_resourcegroup_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_resourcegroups_list')),
            self.client.post(reverse('planner_resourcegroups_list')),
            self.client.get(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_401_UNAUTHORIZED)

    def test_get_resourcegroups(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        resourcegrouphelper.given_resource_group_exists(user1)
        resourcegrouphelper.given_resource_group_exists(user2)
        resourcegrouphelper.given_resource_group_exists(user2)

        # WHEN
        response = self.client.get(reverse('planner_resourcegroups_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ResourceGroup.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_resourcegroup(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('planner_resourcegroups_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ResourceGroup.objects.count(), 1)
        resource_group = ResourceGroup.objects.get(pk=response.data['id'])
        data.update({'user': user.pk})
        resourcegrouphelper.verify_resource_group_matches_data(self, resource_group, data)
        resourcegrouphelper.verify_resource_group_matches_data(self, resource_group, response.data)

    def test_get_resourcegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)

        # WHEN
        response = self.client.get(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resourcegrouphelper.verify_resource_group_matches_data(self, resource_group, response.data)

    def test_update_resourcegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)
        self.assertEqual(resource_group.title, '📚 Test Material Group')
        self.assertTrue(resource_group.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False
        }
        response = self.client.put(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        resource_group.refresh_from_db()
        resourcegrouphelper.verify_resource_group_matches_data(self, resource_group, response.data)

    def test_delete_resourcegroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group = resourcegrouphelper.given_resource_group_exists(user)

        # WHEN
        response = self.client.delete(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ResourceGroup.objects.filter(pk=resource_group.pk).exists())
        self.assertEqual(ResourceGroup.objects.count(), 0)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        resource_group = resourcegrouphelper.given_resource_group_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk})),
            self.client.put(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk})),
            self.client.delete(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk}))
        ]

        # THEN
        self.assertTrue(ResourceGroup.objects.filter(pk=resource_group.pk, user_id=user1.pk).exists())
        commonhelper.verify_all_responses_have_status(self, responses, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        resource_group = resourcegrouphelper.given_resource_group_exists(user2)

        # WHEN
        data = {
            'user': user1.pk,
            # Intentionally NOT changing these value
            'title': resource_group.title,
        }
        response = self.client.put(reverse('planner_resourcegroups_detail', kwargs={'pk': resource_group.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        resource_group.refresh_from_db()
        self.assertEqual(resource_group.get_user().pk, user2.pk)

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_authenticated(self.client)

        responses = [
            self.client.get(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_resourcegroups_detail', kwargs={'pk': '9999'}))
        ]

        commonhelper.verify_responses_hide_other_users_data(self, responses)

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        resource_group1 = resourcegrouphelper.given_resource_group_exists(user)
        resource_group2 = resourcegrouphelper.given_resource_group_exists(user, title='Material Group 2')
        resource_group3 = resourcegrouphelper.given_resource_group_exists(user, title='Material Group 3')

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        ResourceGroup.objects.filter(pk=resource_group1.pk).update(updated_at=old_time)
        ResourceGroup.objects.filter(pk=resource_group2.pk).update(updated_at=recent_time)
        ResourceGroup.objects.filter(pk=resource_group3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_resourcegroups_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(resource_group2.pk, returned_ids)
        self.assertIn(resource_group3.pk, returned_ids)
        self.assertNotIn(resource_group1.pk, returned_ids)

    def test_filter_id_cannot_access_other_users_data(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        resource_group = resourcegrouphelper.given_resource_group_exists(user1)

        # WHEN
        response = self.client.get(reverse('planner_resourcegroups_list') + f'?id={resource_group.pk}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)
