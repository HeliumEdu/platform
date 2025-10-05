__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import json
from unittest import mock

from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class TestCaseStatusViews(APITestCase):
    @mock.patch('health_check.db.backends.DatabaseBackend.check_status')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    @mock.patch('health_check.contrib.s3boto3_storage.backends.S3Boto3StorageHealthCheck.check_status')
    def test_status(self, mock_s3, mock_celery, mock_cache, mock_db):
        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 4)
        self.assertEqual(content['status'], 'operational')

        for component in content['components']:
            self.assertEqual(content['components'][component]['status'], 'operational')

    @mock.patch('health_check.db.models.TestModel.objects.create')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    @mock.patch('health_check.contrib.s3boto3_storage.backends.S3Boto3StorageHealthCheck.check_status')
    def test_status_critical_fails(self, mock_s3, mock_celery, mock_cache, mock_db):
        # GIVEN
        mock_db.side_effect = IntegrityError("Database integrity error")

        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(len(content['components']), 4)
        self.assertEqual(content['status'], 'minor_outage')

        for component in content['components']:
            if component == 'Database':
                self.assertEqual(content['components'][component]['status'], 'minor_outage')

    @mock.patch('health_check.db.backends.DatabaseBackend.check_status')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.s3boto3_storage.backends.S3Boto3StorageHealthCheck.check_status')
    def test_status_exclude_worker(self, mock_s3, mock_cache, mock_db):
        # WHEN
        response = self.client.get(reverse('resource_status') + '?TaskProcessing=false')

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 3)
        self.assertEqual(content['status'], 'operational')

    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    def test_status_worker_only(self, mock_celery):
        # WHEN
        response = self.client.get(reverse('resource_status') + '?Database=false&Cache=false&AWS=false')

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 1)
        self.assertEqual(content['status'], 'operational')

    @mock.patch('health_check.backends.BaseHealthCheckBackend.check_status')
    def test_health(self, mock_check_status):
        # WHEN
        response = self.client.get(reverse('resource_health'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 6)
        self.assertEqual(content['status'], 'operational')
