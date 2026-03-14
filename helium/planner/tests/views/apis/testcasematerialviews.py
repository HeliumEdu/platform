__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
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

    def test_updated_at_filter(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material1 = materialhelper.given_material_exists(material_group)
        material2 = materialhelper.given_material_exists(material_group, title='Material 2')
        material3 = materialhelper.given_material_exists(material_group, title='Material 3')

        # Manually set updated_at to different times
        old_time = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        recent_time = datetime.datetime(2025, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        Material.objects.filter(pk=material1.pk).update(updated_at=old_time)
        Material.objects.filter(pk=material2.pk).update(updated_at=recent_time)
        Material.objects.filter(pk=material3.pk).update(updated_at=recent_time)

        # WHEN
        filter_time = '2024-01-01T00:00:00'
        response = self.client.get(
            reverse('planner_materials_list') + f'?updated_at__gte={filter_time}')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        returned_ids = {item['id'] for item in response.data}
        self.assertIn(material2.pk, returned_ids)
        self.assertIn(material3.pk, returned_ids)
        self.assertNotIn(material1.pk, returned_ids)


class TestCaseMaterialNotesDualWrite(APITestCase):
    """Test dual-write functionality: Material.notes <-> Note table sync."""

    def test_create_material_with_notes_creates_note_entity(self):
        # GIVEN
        from helium.planner.models import Note, NoteLink
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)

        # WHEN
        notes_content = {'ops': [{'insert': 'My material notes\n'}]}
        data = {
            'title': 'Material With Notes',
            'status': enums.ORDERED,
            'condition': enums.USED_GOOD,
            'website': '',
            'price': '0.00',
            'courses': [],
            'notes': notes_content,
            'material_group': material_group.pk,
        }
        response = self.client.post(
            reverse('planner_materialgroups_materials_list',
                    kwargs={'material_group': material_group.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        material = Material.objects.get(pk=response.data['id'])
        self.assertEqual(material.notes, notes_content)

        # Verify Note and NoteLink were created
        self.assertTrue(material.note_links.exists())
        note = material.note_links.first().note
        self.assertEqual(note.content, notes_content)
        self.assertEqual(note.user, user)

    def test_update_material_notes_syncs_to_note_entity(self):
        # GIVEN
        from helium.planner.models import Note, NoteLink
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # Create initial note link
        initial_content = {'ops': [{'insert': 'Initial notes\n'}]}
        note = Note.objects.create(title='Test', content=initial_content, user=user)
        NoteLink.objects.create(note=note, material=material)

        # WHEN - update notes via material API
        new_content = {'ops': [{'insert': 'Updated notes\n'}]}
        data = {
            'title': material.title,
            'status': material.status,
            'condition': material.condition,
            'website': material.website,
            'price': str(material.price),
            'courses': [],
            'notes': new_content,
            'material_group': material_group.pk,
        }
        response = self.client.put(
            reverse('planner_materialgroups_materials_detail',
                    kwargs={'material_group': material_group.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        note.refresh_from_db()
        self.assertEqual(note.content, new_content)

    def test_clear_material_notes_deletes_note_entity(self):
        # GIVEN
        from helium.planner.models import Note, NoteLink
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        material_group = materialgrouphelper.given_material_group_exists(user)
        material = materialhelper.given_material_exists(material_group)

        # Create note link
        note = Note.objects.create(
            title='Test',
            content={'ops': [{'insert': 'Some notes\n'}]},
            user=user
        )
        NoteLink.objects.create(note=note, material=material)
        note_pk = note.pk

        # WHEN - clear notes via material API
        data = {
            'title': material.title,
            'status': material.status,
            'condition': material.condition,
            'website': material.website,
            'price': str(material.price),
            'courses': [],
            'notes': {},  # Empty notes
            'material_group': material_group.pk,
        }
        response = self.client.put(
            reverse('planner_materialgroups_materials_detail',
                    kwargs={'material_group': material_group.pk, 'pk': material.pk}),
            json.dumps(data),
            content_type='application/json')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Note.objects.filter(pk=note_pk).exists())
        self.assertFalse(material.note_links.exists())
