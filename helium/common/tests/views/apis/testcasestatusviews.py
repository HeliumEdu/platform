import json

from django.db import IntegrityError
from django.urls import reverse
from mock import mock
from rest_framework import status
from rest_framework.test import APITestCase

from helium.common.tests.helpers import commonhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.22'


class TestCaseStatusViews(APITestCase):
    @mock.patch('health_check.db.backends.DatabaseBackend.check_status')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    @mock.patch('health_check.contrib.s3boto_storage.backends.S3BotoStorageHealthCheck.check_status')
    @mock.patch('health_check.contrib.twilio.backends.TwilioHealthCheck.check_status')
    def test_status(self, mock_twilio, mock_s3, mock_celery, mock_cache, mock_db):
        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 5)
        self.assertEqual(content['status'], 'operational')

        for component in content['components']:
            self.assertEqual(content['components'][component]['status'], 'operational')

    @mock.patch('health_check.db.models.TestModel.objects.create')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    @mock.patch('health_check.contrib.s3boto_storage.backends.S3BotoStorageHealthCheck.check_status')
    @mock.patch('health_check.contrib.twilio.backends.TwilioHealthCheck.check_status')
    def test_status_critical_fails(self, mock_twilio, mock_s3, mock_celery, mock_cache, mock_db):
        # GIVEN
        mock_db.side_effect = IntegrityError("Database integrity error")

        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(len(content['components']), 5)
        self.assertEqual(content['status'], 'minor_outage')

        for component in content['components']:
            if component == 'Database':
                self.assertEqual(content['components'][component]['status'], 'minor_outage')

    @mock.patch('health_check.db.backends.DatabaseBackend.check_status')
    @mock.patch('health_check.cache.backends.CacheBackend.check_status')
    @mock.patch('health_check.contrib.celery.backends.CeleryHealthCheck.check_status')
    @mock.patch('health_check.contrib.s3boto_storage.backends.S3BotoStorageHealthCheck.check_status')
    @mock.patch('health_check.contrib.twilio.backends.urlopen')
    def test_status_uncritical_fails(self, mock_twilio, mock_s3, mock_celery, mock_cache, mock_db):
        # GIVEN
        commonhelper.given_urlopen_response_value(status.HTTP_404_NOT_FOUND, mock_twilio)

        # WHEN
        response = self.client.get(reverse('resource_status'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 5)
        # Since this is a non-critical service, it will not cause the entire status check to fail, only the component
        self.assertEqual(content['status'], 'operational')

        for component in content['components']:
            if component == 'Twilio':
                self.assertEqual(content['components'][component]['status'], 'major_outage')

    @mock.patch('health_check.backends.BaseHealthCheckBackend.check_status')
    def test_health(self, mock_check_status):
        # WHEN
        response = self.client.get(reverse('resource_health'))

        # THEN
        content = json.loads(response.content.decode('utf-8'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(content['components']), 7)
        self.assertEqual(content['status'], 'operational')
