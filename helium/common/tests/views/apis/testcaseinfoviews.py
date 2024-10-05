__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.7.0"

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
        self.assertEqual(settings.PROJECT_TAGLINE, response.data['tagline'])
        self.assertEqual(settings.PROJECT_VERSION, response.data['version'])
        self.assertEqual(settings.EMAIL_ADDRESS, response.data['support_email'])
        self.assertEqual(settings.SUPPORT_REDIRECT_URL, response.data['support_url'])
        self.assertEqual(settings.BUG_REPORT_REDIRECT_URL, response.data['bug_report_url'])
        self.assertEqual(settings.MAX_UPLOAD_SIZE, response.data['max_upload_size'])
