__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from datetime import timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from helium.common.health import (
    IdentifiedDatabaseBackend,
    IdentifiedCacheBackend,
    IdentifiedS3Boto3StorageHealthCheck,
    IdentifiedCeleryHealthCheck,
    IdentifiedCeleryBeatHealthCheck,
)


class TestCaseHealth(TestCase):
    def test_database_backend_identifier(self):
        # GIVEN
        backend = IdentifiedDatabaseBackend()

        # WHEN
        identifier = backend.identifier()

        # THEN
        self.assertEqual(identifier, 'Database')

    def test_cache_backend_identifier(self):
        # GIVEN
        backend = IdentifiedCacheBackend()

        # WHEN
        identifier = backend.identifier()

        # THEN
        self.assertEqual(identifier, 'Cache')

    def test_s3_backend_identifier(self):
        # GIVEN
        backend = IdentifiedS3Boto3StorageHealthCheck()

        # WHEN
        identifier = backend.identifier()

        # THEN
        self.assertEqual(identifier, 'Storage')

    def test_celery_backend_identifier(self):
        # GIVEN
        backend = IdentifiedCeleryHealthCheck()

        # WHEN
        identifier = backend.identifier()

        # THEN
        self.assertEqual(identifier, 'TaskProcessing')

    def test_celery_beat_backend_identifier(self):
        # GIVEN
        backend = IdentifiedCeleryBeatHealthCheck()

        # WHEN
        identifier = backend.identifier()

        # THEN
        self.assertEqual(identifier, 'CeleryBeat')

    @mock.patch('helium.common.health.TaskResult.objects.filter')
    def test_celery_beat_check_status_healthy(self, mock_filter):
        # GIVEN
        backend = IdentifiedCeleryBeatHealthCheck()
        mock_filter.return_value.exists.return_value = True

        # WHEN
        backend.check_status()

        # THEN
        self.assertEqual(len(backend.errors), 0)

    @mock.patch('helium.common.health.TaskResult.objects.filter')
    def test_celery_beat_check_status_unhealthy(self, mock_filter):
        # GIVEN
        backend = IdentifiedCeleryBeatHealthCheck()
        mock_filter.return_value.exists.return_value = False

        # WHEN
        backend.check_status()

        # THEN
        self.assertEqual(len(backend.errors), 1)

    @mock.patch('helium.common.health.TaskResult.objects.filter')
    def test_celery_beat_check_status_exception(self, mock_filter):
        # GIVEN
        from health_check.exceptions import HealthCheckException
        backend = IdentifiedCeleryBeatHealthCheck()
        mock_filter.side_effect = Exception('DB error')

        # WHEN/THEN
        with self.assertRaises(HealthCheckException):
            backend.check_status()
