import mock
from django.conf import settings
from django.core.exceptions import SuspiciousOperation, PermissionDenied, ViewDoesNotExist
from django.test import TestCase, override_settings
from django.urls import reverse
from maintenance_mode.core import set_maintenance_mode
from rest_framework import status

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


class TestCaseErrorViews(TestCase):
    @mock.patch('helium.common.views.generalviews.metricutils')
    def test_internal_server_error(self, metricutils):
        # GIVEN
        metricutils.increment.side_effect = SuspiciousOperation("Bad request.")

        # WHEN
        response = self.client.get(reverse('home'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTemplateUsed(response, 'errors/400.html')

    @mock.patch('helium.common.views.generalviews.metricutils')
    def test_internal_forbidden(self, metricutils):
        # GIVEN
        metricutils.increment.side_effect = PermissionDenied("Forbidden.")

        # WHEN
        response = self.client.get(reverse('home'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTemplateUsed(response, 'errors/403.html')

    def test_not_found(self):
        # WHEN
        response = self.client.get('/not-a-real-url')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTemplateUsed(response, 'errors/404.html')

    @mock.patch('helium.common.views.generalviews.metricutils')
    def test_internal_server_error(self, metricutils):
        # GIVEN
        metricutils.increment.side_effect = ViewDoesNotExist("Internal server error.")
        # By default, the test client will re-raise an exception when testing (instead of rendering the 500 page), so
        # we want to override that setting
        self.client.store_exc_info = lambda *args, **kwargs: True

        # WHEN
        response = self.client.get(reverse('home'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertTemplateUsed(response, 'errors/500.html')

    @override_settings(MAINTENANCE_MODE_IGNORE_TESTS=False)
    def test_maintenance_mode(self):
        # GIVEN
        set_maintenance_mode(True)

        # WHEN
        response = self.client.get(reverse('login'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertTemplateUsed(response, settings.MAINTENANCE_MODE_TEMPLATE)

        # CLEANUP
        set_maintenance_mode(False)
