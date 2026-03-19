__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import TestCase
from rest_framework.exceptions import Throttled, ValidationError

from helium.common.handlers.exceptions import helium_exception_handler


class TestCaseExceptions(TestCase):
    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_singular(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=1)
        context = {}
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Request was throttled. Try again in 1 second.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_plural(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=5.7)
        context = {}
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Request was throttled. Try again in 6 seconds.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_without_wait(self, mock_handler):
        # GIVEN
        exc = Throttled()
        exc.wait = None
        context = {}
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Request was throttled. Try again later.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_non_throttled_exception(self, mock_handler):
        # GIVEN
        exc = ValidationError('Invalid data')
        context = {}
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        mock_handler.assert_called_once_with(exc, context)
