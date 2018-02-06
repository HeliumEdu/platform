import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import MaterialGroup
from helium.planner.tests.helpers import materialgrouphelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseMaterialGroupViews(TestCase):
    def test_materialgroup_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_materialgroups_list')),
            self.client.post(reverse('api_planner_materialgroups_list')),
            self.client.get(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_materialgroups(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        materialgrouphelper.given_material_group_exists(user1)
        materialgrouphelper.given_material_group_exists(user2)
        materialgrouphelper.given_material_group_exists(user2)

        # WHEN
        response = self.client.get(reverse('api_planner_materialgroups_list'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(MaterialGroup.objects.count(), 3)
        self.assertEqual(len(response.data), 2)

    def test_create_materialgroup(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)

        # WHEN
        data = {
            'title': 'some title',
            'shown_on_calendar': False,
        }
        response = self.client.post(reverse('api_planner_materialgroups_list'), json.dumps(data),
                                    content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MaterialGroup.objects.count(), 1)
        material_group = MaterialGroup.objects.get(pk=response.data['id'])
        data.update({'user': user.pk})
        materialgrouphelper.verify_material_group_matches_data(self, material_group, data)
        materialgrouphelper.verify_material_group_matches_data(self, material_group, response.data)

    def test_get_materialgroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        response = self.client.get(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        materialgrouphelper.verify_material_group_matches_data(self, material_group, response.data)

    def test_update_materialgroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        self.assertEqual(material_group.title, 'Test Material Group')
        self.assertTrue(material_group.shown_on_calendar)

        # WHEN
        data = {
            'title': 'new title',
            'shown_on_calendar': False
        }
        response = self.client.put(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk}),
                                   json.dumps(data),
                                   content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertDictContainsSubset(data, response.data)
        material_group = MaterialGroup.objects.get(pk=material_group.pk)
        materialgrouphelper.verify_material_group_matches_data(self, material_group, response.data)

    def test_delete_materialgroup_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        response = self.client.delete(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(MaterialGroup.objects.filter(pk=material_group.pk).exists())
        self.assertEqual(MaterialGroup.objects.count(), 0)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        material_group = materialgrouphelper.given_material_group_exists(user1)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk})),
            self.client.put(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk})),
            self.client.delete(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk}))
        ]

        # THEN
        self.assertTrue(MaterialGroup.objects.filter(pk=material_group.pk, user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_read_only_field_does_nothing(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        material_group = materialgrouphelper.given_material_group_exists(user2)

        # WHEN
        data = {
            'user': user1.pk,
            # Intentionally NOT changing these value
            'title': material_group.title,
        }
        response = self.client.put(reverse('api_planner_materialgroups_detail', kwargs={'pk': material_group.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        material_group = MaterialGroup.objects.get(pk=material_group.id)
        self.assertEqual(material_group.get_user().pk, user2.pk)

    def test_not_found(self):
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        responses = [
            self.client.get(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'})),
            self.client.put(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_materialgroups_detail', kwargs={'pk': '9999'}))
        ]

        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())
