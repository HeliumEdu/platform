__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.29"

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from helium.auth.tests.helpers import userhelper


class TestCasePrivateFeedResourceViews(APITestCase):
    def test_private_url_resource_login_required(self):
        # GIVEN
        userhelper.given_a_user_exists()

        # WHEN
        responses = [
            self.client.put(reverse('feed_private_resource_enable')),
            self.client.put(reverse('feed_private_resource_disable'))
        ]

        # THEN
        for response in responses:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_enable_private_url(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)

        # WHEN
        response = self.client.put(reverse('feed_private_resource_enable'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = get_user_model().objects.get(pk=user.pk)
        self.assertIsNotNone(user.settings.private_slug)
        self.assertIn('events_private_url', response.data)
        self.assertIn('homework_private_url', response.data)
        self.assertIn('courseschedules_private_url', response.data)
        self.assertEqual(self.client.get(response.data['events_private_url']).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(response.data['homework_private_url']).status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get(response.data['courseschedules_private_url']).status_code, status.HTTP_200_OK)

    def test_disable_private_url(self):
        # GIVEN
        user = userhelper.given_a_user_exists_and_is_authenticated(self.client)
        user.settings.enable_private_slug()
        private_slug = user.settings.private_slug

        # WHEN
        response = self.client.put(reverse('feed_private_resource_disable'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        user = get_user_model().objects.get(pk=user.pk)
        self.assertIsNone(user.settings.private_slug)
        self.assertEqual(
            self.client.get(reverse('feed_private_events_ical', kwargs={'slug': private_slug})).status_code,
            status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.get(reverse('feed_private_homework_ical', kwargs={'slug': private_slug})).status_code,
            status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            self.client.get(reverse('feed_private_courseschedules_ical', kwargs={'slug': private_slug})).status_code,
            status.HTTP_404_NOT_FOUND)
