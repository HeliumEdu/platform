import os

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper
from helium.planner.models import Attachment
from helium.planner.tests.helpers import coursegrouphelper, coursehelper, attachmenthelper, eventhelper, homeworkhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.4'


class TestCaseAttachmentViews(APITestCase):
    def setUp(self):
        self.tmp_files = []

    def tearDown(self):
        attachmenthelper.cleanup_attachments()

    def test_attachment_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.get(reverse('planner_attachments_list')),
            self.client.post(reverse('planner_attachments_list')),
            self.client.get(reverse('planner_attachments_detail', kwargs={'pk': '9999'})),
            self.client.delete(reverse('planner_attachments_detail', kwargs={'pk': '9999'}))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_attachments(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        event1 = eventhelper.given_event_exists(user1)
        event2 = eventhelper.given_event_exists(user2)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        course2 = coursehelper.given_course_exists(course_group2)
        course3 = coursehelper.given_course_exists(course_group2)
        homework1 = homeworkhelper.given_homework_exists(course1)
        homework2 = homeworkhelper.given_homework_exists(course2)
        attachmenthelper.given_attachment_exists(user1, course=course1)
        attachmenthelper.given_attachment_exists(user2, course=course2)
        attachmenthelper.given_attachment_exists(user2, course=course3)
        attachmenthelper.given_attachment_exists(user2, course=course3)
        attachmenthelper.given_attachment_exists(user1, event=event1)
        attachmenthelper.given_attachment_exists(user2, event=event2)
        attachmenthelper.given_attachment_exists(user2, event=event2)
        attachmenthelper.given_attachment_exists(user1, homework=homework1)
        attachmenthelper.given_attachment_exists(user2, homework=homework2)
        attachmenthelper.given_attachment_exists(user2, homework=homework2)

        # WHEN
        response1 = self.client.get(reverse('planner_attachments_list'))
        response2 = self.client.get(reverse('planner_attachments_list') + '?course={}'.format(course3.pk))
        response3 = self.client.get(reverse('planner_attachments_list') + '?event={}'.format(event2.pk))
        response4 = self.client.get(reverse('planner_attachments_list') + '?homework={}'.format(homework2.pk))

        # THEN
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response3.status_code, status.HTTP_200_OK)
        self.assertEqual(response4.status_code, status.HTTP_200_OK)
        self.assertEqual(Attachment.objects.count(), 10)
        self.assertEqual(len(response1.data), 7)
        self.assertEqual(len(response2.data), 2)
        self.assertEqual(len(response3.data), 2)
        self.assertEqual(len(response4.data), 2)

    def test_create_course_attachment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
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
                reverse('planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], os.path.basename(tmp_file.name))
        self.assertEqual(response.data[0]['size'], os.path.getsize(tmp_file.name))
        self.assertEqual(response.data[0]['course'], data['course'])
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.get(pk=response.data[0]['id'])
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data[0])

    def test_create_event_attachment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        event = eventhelper.given_event_exists(user)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'event': event.pk,
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], os.path.basename(tmp_file.name))
        self.assertEqual(response.data[0]['size'], os.path.getsize(tmp_file.name))
        self.assertEqual(response.data[0]['event'], data['event'])
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.get(pk=response.data[0]['id'])
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data[0])

    def test_create_homework_attachment(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        homework = homeworkhelper.given_homework_exists(course)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'homework': homework.pk,
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], os.path.basename(tmp_file.name))
        self.assertEqual(response.data[0]['size'], os.path.getsize(tmp_file.name))
        self.assertEqual(response.data[0]['homework'], data['homework'])
        self.assertEqual(Attachment.objects.count(), 1)
        attachment = Attachment.objects.get(pk=response.data[0]['id'])
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data[0])

    def test_create_orphaned_attachment_fails(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_authenticated(self.client)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name) as fp:
            data = {
                'file[]': [fp]
            }
            response = self.client.post(
                reverse('planner_attachments_list'),
                data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('One of', response.data[0]['non_field_errors'][0])

    def test_get_attachment_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        attachment = attachmenthelper.given_attachment_exists(user, course)

        # WHEN
        response = self.client.get(reverse('planner_attachments_detail', kwargs={'pk': attachment.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachmenthelper.verify_attachment_matches_data(self, attachment, response.data)

    def test_delete_attachment_by_id(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        course_group = coursegrouphelper.given_course_group_exists(user)
        course = coursehelper.given_course_exists(course_group)
        attachment = attachmenthelper.given_attachment_exists(user, course)

        # WHEN
        response = self.client.delete(reverse('planner_attachments_detail', kwargs={'pk': attachment.pk}))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())
        self.assertEqual(Attachment.objects.count(), 0)

    def test_related_field_owned_by_another_user_forbidden(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        tmp_file = attachmenthelper.given_file_exists()

        # WHEN
        with open(tmp_file.name):
            response = self.client.post(reverse('planner_attachments_list'), {'course': course1.pk})

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_access_object_owned_by_another_user(self):
        # GIVEN
        user1 = userhelper.given_a_user_exists()
        user2 = userhelper.given_a_user_exists_and_is_authenticated(self.client, username='user2',
                                                                    email='test2@email.com')
        event = eventhelper.given_event_exists(user1)
        course_group1 = coursegrouphelper.given_course_group_exists(user1)
        course_group2 = coursegrouphelper.given_course_group_exists(user2)
        course1 = coursehelper.given_course_exists(course_group1)
        coursehelper.given_course_exists(course_group2)
        homework = homeworkhelper.given_homework_exists(course1)
        attachment1 = attachmenthelper.given_attachment_exists(user1, course=course1)
        attachmenthelper.given_attachment_exists(user1, homework=homework)
        attachmenthelper.given_attachment_exists(user1, event=event)

        # WHEN
        responses = [
            self.client.get(reverse('planner_attachments_list') + '?course={}'.format(course1.pk)),
            self.client.get(reverse('planner_attachments_list') + '?event={}'.format(event.pk)),
            self.client.get(reverse('planner_attachments_list') + '?homework={}'.format(homework.pk)),
            self.client.delete(reverse('planner_attachments_detail', kwargs={'pk': attachment1.pk}))
        ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
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
            'course': course.pk
        }
        response = self.client.post(
            reverse('planner_attachments_list'),
            data)

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('details', response.data)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_not_found(self):
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
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
                self.client.post(reverse('planner_attachments_list'), data),
                self.client.get(reverse('planner_attachments_detail', kwargs={'pk': '9999'})),
                self.client.delete(reverse('planner_attachments_detail', kwargs={'pk': '9999'}))
            ]

        # THEN
        for response in responses:
            if isinstance(response.data, list):
                self.assertEqual(len(response.data), 0)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertIn('not found', response.data['detail'].lower())
