"""
Tests for error views.
"""
from unittest import skip

import mock
from django.core.exceptions import SuspiciousOperation, PermissionDenied, ViewDoesNotExist
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from helium.auth.tests.helpers import userhelper

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


class TestCaseErrorViews(TestCase):
    def test_not_found(self):
        # WHEN
        response = self.client.get('/not-a-real-url')

        # THEN
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTemplateUsed(response, 'errors/404.html')

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
        self.client.store_exc_info = lambda *args, **kwargs: True

        # WHEN
        response = self.client.get(reverse('home'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTemplateUsed(response, 'errors/403.html')

    @mock.patch('helium.common.views.generalviews.metricutils')
    def test_internal_server_error(self, metricutils):
        # GIVEN
        metricutils.increment.side_effect = ViewDoesNotExist("Internal server error.")
        self.client.store_exc_info = lambda *args, **kwargs: True

        # WHEN
        response = self.client.get(reverse('home'))

        # THEN
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertTemplateUsed(response, 'errors/500.html')

    @skip('Middleware is being ignored, need to debug')
    def test_maintenance_mode(self):
        # GIVEN
        userhelper.given_a_user_exists_and_is_logged_in(self.client)

        with self.settings(MAINTENANCE_MODE_IGNORE_TESTS=False, MAINTENANCE_MODE=True):
            # WHEN
            response = self.client.get(reverse('settings'))

            # THEN
            self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertTemplateUsed(response, 'errors/maintenance.html')
