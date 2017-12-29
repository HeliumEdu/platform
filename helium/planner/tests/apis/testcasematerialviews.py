"""
Tests for Material interaction.
"""
import json

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Material
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, materialgrouphelper, materialhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseAPIMaterialViews(TestCase):
    def test_material_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_materials_list')),
            self.client.get(reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': '9999'})),
            self.client.post(
                reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': '9999'})),
            self.client.get(
                reverse('api_planner_materialgroups_materials_detail',
                        kwargs={'material_group_id': '9999', 'pk': '9999'})),
            self.client.put(
                reverse('api_planner_materialgroups_materials_detail',
                        kwargs={'material_group_id': '9999', 'pk': '9999'})),
            self.client.delete(
                reverse('api_planner_materialgroups_materials_detail',
                        kwargs={'material_group_id': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_materials(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        material_group1 = materialgrouphelper.given_material_group_exists(user1)
        material_group2 = materialgrouphelper.given_material_group_exists(user2)
        material_group3 = materialgrouphelper.given_material_group_exists(user2)
        materialhelper.given_material_exists(material_group1)
        materialhelper.given_material_exists(material_group2)
        materialhelper.given_material_exists(material_group3)
        materialhelper.given_material_exists(material_group3)

        # WHEN
        response1 = self.client.get(reverse('api_planner_materials_list'))
        response2 = self.client.get(
            reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': material_group3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Material.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_material(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        data = {
            'title': 'some title',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
            'website': 'http://www.some-material.com',
            'price': '500.27',
            'details': 'N/A',
            'seller_details': 'Email: carl@email.com',
            'material_group': material_group.pk,
            'courses': course.pk
        }
        response = self.client.post(
            reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': material_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Material.objects.count(), 1)
        material = Material.objects.get(pk=response.data['id'])
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_get_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        response = self.client.get(reverse('api_planner_materialgroups_materials_detail',
                                           kwargs={'material_group_id': material_group.pk, 'pk': material.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_update_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        material_group1 = materialgrouphelper.given_material_group_exists(user)
        material_group2 = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group1, courses=[course1])

        # WHEN
        data = {
            'title': 'some title',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
            'website': 'http://www.some-material.com',
            'price': 500.27,
            'details': 'N/A',
            'seller_details': 'Email: carl@email.com',
            'material_group': material_group2.pk,
            'courses': course2.pk
        }
        response = self.client.put(
            reverse('api_planner_materialgroups_materials_detail',
                    kwargs={'material_group_id': material_group1.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['material_group'], data['material_group'])
        self.assertEqual(response.data['courses'], [data['courses']])
        material = Material.objects.get(pk=material.pk)
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_update_multiple_courses(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        material_group1 = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group1)

        # WHEN
        data = {
            'courses': ','.join([str(course1.pk), str(course2.pk)]),
            # Intentionally NOT changing these value
            'material_group': material.material_group.pk
        }
        response = self.client.put(
            reverse('api_planner_materialgroups_materials_detail',
                    kwargs={'material_group_id': material_group1.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        course_ids = data['courses'].split(',')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data['courses']), len(course_ids))
        for i, course_id in enumerate(response.data['courses']):
            self.assertEqual(course_id, int(course_ids[i]))
        material = Material.objects.get(pk=material.pk)
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_delete_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        response = self.client.delete(reverse('api_planner_materialgroups_materials_detail',
                                              kwargs={'material_group_id': material_group.pk, 'pk': material.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Material.objects.filter(pk=material_group.pk).exists())
        self.assertEqual(Material.objects.count(), 0)

    def test_ownership_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user1')
        user2 = userhelper.given_a_user_exists(username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        material_group1 = materialgrouphelper.given_material_group_exists(user1)
        material_group2 = materialgrouphelper.given_material_group_exists(user2)
        material = materialhelper.given_material_exists(material_group1, courses=[course1])

        # WHEN
        responses = [
            self.client.post(
                reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': material_group1.pk}),
                json.dumps({
                    'title': 'some title',
                    'status': enums.TO_SELL,
                    'condition': enums.USED_POOR,
                    'website': 'http://www.some-material.com',
                    'price': 500.27,
                    'details': 'N/A',
                    'seller_details': 'Email: carl@email.com',
                    'courses': course2.pk
                }),
                content_type='application/json'),
            self.client.post(
                reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': material_group2.pk}),
                json.dumps({}),
                content_type='application/json'),
            self.client.put(
                reverse('api_planner_materialgroups_materials_detail',
                        kwargs={'material_group_id': material_group1.pk, 'pk': material.pk}),
                json.dumps(
                    {
                        'material_group': material_group2.pk
                    }),
                content_type='application/json'),
            self.client.put(
                reverse('api_planner_materialgroups_materials_detail',
                        kwargs={'material_group_id': material_group1.pk, 'pk': material.pk}),
                json.dumps(
                    {
                        'courses': course2.pk,
                        # Intentionally NOT changing these value
                        'material_group': material.material_group.pk
                    }),
                content_type='application/json')
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_error_on_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        material_group = materialgrouphelper.given_material_group_exists(user1)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_materialgroups_materials_list',
                                    kwargs={'material_group_id': material_group.pk})),
            self.client.post(reverse('api_planner_materialgroups_materials_list',
                                     kwargs={'material_group_id': material_group.pk})),
            self.client.get(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': material_group.pk, 'pk': material.pk})),
            self.client.put(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': material_group.pk, 'pk': material.pk})),
            self.client.delete(reverse('api_planner_materialgroups_materials_detail',
                                       kwargs={'material_group_id': material_group.pk, 'pk': material.pk}))
        ]

        # THEN
        self.assertTrue(Material.objects.filter(pk=material.pk, material_group__user_id=user1.pk).exists())
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        data = {
            'status': 'not-a-valid-status',
        }
        response = self.client.post(
            reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': material_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        self.assertEqual(Material.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)
        material_status = material.status

        # WHEN
        data = {
            'status': 'not-a-valid-status',
        }
        response = self.client.put(reverse('api_planner_materialgroups_materials_detail',
                                           kwargs={'material_group_id': material_group.pk, 'pk': material.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        material = Material.objects.get(id=material.id)
        self.assertEqual(material.status, material_status)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        responses = [
            self.client.get(reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': '9999'})),
            self.client.post(
                reverse('api_planner_materialgroups_materials_list', kwargs={'material_group_id': '9999'})),
            self.client.get(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': '9999', 'pk': '9999'})),
            self.client.put(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': '9999', 'pk': '9999'})),
            self.client.get(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': material_group.pk, 'pk': '9999'})),
            self.client.put(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': material_group.pk, 'pk': '9999'})),
            self.client.get(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': '9999', 'pk': material.pk})),
            self.client.put(reverse('api_planner_materialgroups_materials_detail',
                                    kwargs={'material_group_id': '9999', 'pk': material.pk}))
        ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('not found', response.data['detail'].lower())
