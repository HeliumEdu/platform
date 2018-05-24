import json

from django.urls import reverse
from mock import mock
from rest_framework import status
from rest_framework.test import APITestCase

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.20'


class TestCaseStatusViews(APITestCase):
    @mock.patch('health_check.backends.BaseHealthCheckBackend.run_check')
    def test_status(self, mock_run_check):
        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 5)
        self.assertEqual(content['status'], 'operational')

    @mock.patch('health_check.backends.BaseHealthCheckBackend.run_check')
    def test_health(self, mock_run_check):
        # WHEN
        response = self.client.get(reverse('resource_health'))

        # THEN
        content = json.loads(response.content)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 7)
        self.assertEqual(content['status'], 'operational')
