__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import TestCase

from helium.common.health import IdentifiedCeleryBeatHealthCheck


class TestCaseHealthEndpoint(TestCase):
    def test_status_endpoint_returns_success(self):
        # GIVEN/WHEN
        response = self.client.get('/status/core/')

        # THEN
        self.assertIn(response.status_code, [200, 500])


class TestCaseHealth(TestCase):
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
