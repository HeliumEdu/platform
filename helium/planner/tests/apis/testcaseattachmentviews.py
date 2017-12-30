"""
Tests for Attachment interaction.
"""
import json
import os

from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Attachment
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, attachmenthelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseAPIAttachmentViews(TestCase):
    def test_attachment_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_courses_attachments_list', kwargs={'course_id': '9999'})),
            self.client.get(reverse('api_planner_attachments_list')),
            self.client.post(reverse('api_planner_attachments_list')),
            self.client.get(reverse('api_planner_attachments_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('api_planner_attachments_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_attachments(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        attachmenthelper.given_attachment_exists(user1, course1)
        attachmenthelper.given_attachment_exists(user2, course2)
        attachmenthelper.given_attachment_exists(user2, course3)
        attachmenthelper.given_attachment_exists(user2, course3)

        # WHEN
        response1 = self.client.get(reverse('api_planner_attachments_list'))
        response2 = self.client.get(reverse('api_planner_courses_attachments_list', kwargs={'course_id': course3.pk}))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(Attachment.objects.count(), 4)
        self.assertEqual(len(response1.data), 3)
        self.assertEqual(len(response2.data), 2)

    def test_create_attachment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'course': course.pk,
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('api_planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], os.path.basename(tmp_file.name))
        self.assertEqual(response.data['size'], os.path.getsize(tmp_file.name))
        self.assertEqual(response.data['course'], data['course'])
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.get(pk=response.data['id'])
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data)

    def test_get_attachment_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        attachment = attachmenthelper.given_attachment_exists(user, course)

        # WHEN
        response = self.client.get(reverse('api_planner_attachments_detail', kwargs={'pk': attachment.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data)

    def test_delete_attachment_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        attachment = attachmenthelper.given_attachment_exists(user, course)

        # WHEN
        response = self.client.delete(reverse('api_planner_attachments_detail', kwargs={'pk': attachment.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())
        self.assertEqual(Attachment.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'course': course1.pk,
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('api_planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists(username='user1')
        user2 = userhelper.given_a_user_exists_and_is_logged_in(self.client, username='user2', email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        attachment = attachmenthelper.given_attachment_exists(user1, course1)

        # WHEN
        responses = [
            self.client.get(reverse('api_planner_courses_attachments_list', kwargs={'course_id': course1.pk})),
            self.client.delete(reverse('api_planner_attachments_detail', kwargs={'pk': attachment.pk}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_bad_data(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)

        # WHEN
        data = {
            'course': course.pk
        }
        response = self.client.post(
            reverse('api_planner_attachments_list'),
            data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_logged_in(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        coursehelper.given_course_exists(course_group)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'course': '9999',
                'file[]': [fp]
            }
            responses = [
                self.client.post(reverse('api_planner_attachments_list'), data),
                self.client.get(reverse('api_planner_courses_attachments_list', kwargs={'course_id': '9999'})),
                self.client.get(reverse('api_planner_attachments_detail', kwargs={'pk': '9999'}))
            ]

        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertIn('not found', response.data['detail'].lower())
