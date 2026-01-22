__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.21"

import json

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.common import enums
from helium.planner.models import Material
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, materialgrouphelper, materialhelper


class TestCaseMaterialViews(APITestCase):
    def test_material_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_materials_list')),
            self.client.get(reverse('planner_materialgroups_materials_list', kwargs={'material_group': '9999'})),
            self.client.post(
                reverse('planner_materialgroups_materials_list', kwargs={'material_group': '9999'})),
            self.client.get(
                reverse('planner_materialgroups_materials_detail',
                        kwargs={'material_group': '9999', 'pk': '9999'})),
            self.client.put(
                reverse('planner_materialgroups_materials_detail',
                        kwargs={'material_group': '9999', 'pk': '9999'})),
            self.client.delete(
                reverse('planner_materialgroups_materials_detail',
                        kwargs={'material_group': '9999', 'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_materials(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        material_group1 = materialgrouphelper.given_material_group_exists(user1)
        material_group2 = materialgrouphelper.given_material_group_exists(user2)
        material_group3 = materialgrouphelper.given_material_group_exists(user2)
        materialhelper.given_material_exists(material_group1)
        materialhelper.given_material_exists(material_group2)
        materialhelper.given_material_exists(material_group3)
        materialhelper.given_material_exists(material_group3)

        # WHEN
        response1 = self.client.get(reverse('planner_materials_list'))
        response2 = self.client.get(
            reverse('planner_materialgroups_materials_list', kwargs={'material_group': material_group3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Material.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_material(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
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
            'material_group': material_group.pk,
            'courses': [course.pk]
        }
        response = self.client.post(
            reverse('planner_materialgroups_materials_list', kwargs={'material_group': material_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Material.objects.count(), 1)
        material = Material.objects.get(pk=response.data['id'])
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_get_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        response = self.client.get(reverse('planner_materialgroups_materials_detail',
                                           kwargs={'material_group': material_group.pk, 'pk': material.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_update_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        material_group1 = materialgrouphelper.given_material_group_exists(user)
        material_group2 = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group1, courses=[course1])
        self.assertEqual(material.title, '📘 Test Material')

        # WHEN
        data = {
            'title': 'some title',
            'status': enums.TO_SELL,
            'condition': enums.USED_POOR,
            'website': 'http://www.some-material.com',
            'price': '500.27',
            'details': 'N/A',
            'material_group': material_group2.pk,
            'courses': [course2.pk]
        }
        response = self.client.put(
            reverse('planner_materialgroups_materials_detail',
                    kwargs={'material_group': material_group1.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, response.data | data)
        material.refresh_from_db()
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_update_multiple_courses(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course1 = coursehelper.given_course_exists(course_group)
        course2 = coursehelper.given_course_exists(course_group)
        material_group1 = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group1)

        # WHEN
        data = {
            'courses': [course1.pk, course2.pk],
            # Intentionally NOT changing these value
            'title': material.title,
            'material_group': material.material_group.pk
        }
        response = self.client.put(
            reverse('planner_materialgroups_materials_detail',
                    kwargs={'material_group': material_group1.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['courses'], data['courses'])
        material.refresh_from_db()
        materialhelper.verify_material_matches_data(self, material, response.data)

    def test_delete_material_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        response = self.client.delete(reverse('planner_materialgroups_materials_detail',
                                              kwargs={'material_group': material_group.pk, 'pk': material.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Material.objects.filter(pk=material_group.pk).exists())
        self.assertEqual(Material.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists_and_is_authenticated(self.client)
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
                reverse('planner_materialgroups_materials_list', kwargs={'material_group': material_group1.pk}),
                json.dumps({'courses': [course2.pk]}),
                content_type='application/json'),
            self.client.post(
                reverse('planner_materialgroups_materials_list', kwargs={'material_group': material_group2.pk}),
                json.dumps({}),
                content_type='application/json'),
            self.client.put(
                reverse('planner_materialgroups_materials_detail',
                        kwargs={'material_group': material_group1.pk, 'pk': material.pk}),
                json.dumps({'material_group': material_group2.pk}),
                content_type='application/json'),
            self.client.put(
                reverse('planner_materialgroups_materials_detail',
                        kwargs={'material_group': material_group1.pk, 'pk': material.pk}),
                json.dumps({'courses': [course2.pk]}),
                content_type='application/json')
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_no_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2', email='test2@email.com')
        material_group = materialgrouphelper.given_material_group_exists(user1)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        responses = [
            self.client.get(reverse('planner_materialgroups_materials_list',
                                    kwargs={'material_group': material_group.pk})),
            self.client.post(reverse('planner_materialgroups_materials_list',
                                     kwargs={'material_group': material_group.pk}),
                             content_type='application/json'),
            self.client.get(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': material_group.pk, 'pk': material.pk})),
            self.client.put(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': material_group.pk, 'pk': material.pk})),
            self.client.delete(reverse('planner_materialgroups_materials_detail',
                                       kwargs={'material_group': material_group.pk, 'pk': material.pk}))
        ]

        # THEN
        self.assertTrue(Material.objects.filter(pk=material.pk, material_group__user_id=user1.pk).exists())
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        data = {
            'status': 'not-a-valid-status'
        }
        response = self.client.post(
            reverse('planner_materialgroups_materials_list', kwargs={'material_group': material_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
        self.assertEqual(Material.objects.count(), 0)

    def test_update_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # WHEN
        data = {
            'status': 'not-a-valid-status'
        }
        response = self.client.put(reverse('planner_materialgroups_materials_detail',
                                           kwargs={'material_group': material_group.pk, 'pk': material.pk}),
                                   json.dumps(data), content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        responses = [
            self.client.get(reverse('planner_materialgroups_materials_list', kwargs={'material_group': '9999'})),
            self.client.post(
                reverse('planner_materialgroups_materials_list', kwargs={'material_group': '9999'}),
                content_type='application/json'),
            self.client.get(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': '9999', 'pk': '9999'})),
            self.client.put(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': '9999', 'pk': '9999'})),
            self.client.delete(reverse('planner_materialgroups_materials_detail',
                                       kwargs={'material_group': '9999', 'pk': '9999'})),
            self.client.get(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': material_group.pk, 'pk': '9999'})),
            self.client.put(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': material_group.pk, 'pk': '9999'})),
            self.client.delete(reverse('planner_materialgroups_materials_detail',
                                       kwargs={'material_group': material_group.pk, 'pk': '9999'})),
            self.client.get(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': '9999', 'pk': material.pk})),
            self.client.put(reverse('planner_materialgroups_materials_detail',
                                    kwargs={'material_group': '9999', 'pk': material.pk})),
            self.client.delete(reverse('planner_materialgroups_materials_detail',
                                       kwargs={'material_group': '9999', 'pk': material.pk}))
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
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group, courses=[course1, course2])

        response = self.client.get(
            reverse('planner_materials_list') + f'?courses={course1.pk}&courses={course2.pk}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['title'], material.title)
