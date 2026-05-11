__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class TestCaseInfoViews(APITestCase):
    def test_info(self):
        # WHEN
        response = self.client.get(reverse('resource_info'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(settings.PROJECT_NAME, response.data['name'])
        self.assertEqual(settings.PROJECT_VERSION, response.data['version'])
        self.assertEqual(settings.MAX_UPLOAD_SIZE, response.data['max_upload_size'])
        self.assertEqual(settings.ACCESS_TOKEN_TTL_MINUTES, response.data['access_token_lifetime_minutes'])
        self.assertEqual(settings.REFRESH_TOKEN_TTL_DAYS, response.data['refresh_token_lifetime_days'])
        self.assertEqual(['google', 'apple'], response.data['oauth_providers'])
        self.assertEqual(['json'], response.data['import_file_types'])
