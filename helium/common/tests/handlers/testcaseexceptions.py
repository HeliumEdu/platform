from unittest import mock

from django.http import Http404
from django.test import TestCase
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, NotFound, PermissionDenied, Throttled, \
    ValidationError
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory
from rest_framework_simplejwt.exceptions import InvalidToken

from helium.common.handlers.exceptions import helium_exception_handler


def _context(client_version=None):
    headers = {'HTTP_X_CLIENT_VERSION': client_version} if client_version else {}
    return {'request': Request(APIRequestFactory().get('/', **headers))}


class TestCaseExceptions(TestCase):
    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_singular(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=1)
        context = _context()
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Too many attempts. Try again in a minute.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_plural(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=150.7)
        context = _context()
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Too many attempts. Try again in 3 minutes.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_of_an_hour(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=3600)
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, _context())

        # THEN
        self.assertEqual(exc.detail, 'Too many attempts. Try again in about an hour.')

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_with_wait_of_hours_rounds_half_hours_up(self, mock_handler):
        # GIVEN
        exc = Throttled(wait=9000)
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, _context())

        # THEN
        self.assertEqual(exc.detail, 'Too many attempts. Try again in about 3 hours.')

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_throttled_without_wait(self, mock_handler):
        # GIVEN
        exc = Throttled()
        exc.wait = None
        context = _context()
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        self.assertEqual(exc.detail, 'Too many attempts. Try again later.')
        mock_handler.assert_called_once_with(exc, context)

    @mock.patch('helium.common.handlers.exceptions.exception_handler')
    def test_non_throttled_exception(self, mock_handler):
        # GIVEN
        exc = ValidationError('Invalid data')
        context = _context()
        mock_handler.return_value = mock.MagicMock()

        # WHEN
        helium_exception_handler(exc, context)

        # THEN
        mock_handler.assert_called_once_with(exc, context)

    def test_field_errors_for_a_legacy_app(self):
        # GIVEN
        exc = ValidationError({'title': ['This field is required.']}, code='required')

        # WHEN
        response = helium_exception_handler(exc, _context(client_version='3.16.12+361'))

        # THEN
        self.assertEqual(response.data, {'title': ['This field is required.']})

    def test_field_errors_with_codes(self):
        # GIVEN
        exc = ValidationError({'title': ['This field is required.'], 'nested': {'start': ['Bad.']}}, code='required')

        # WHEN
        response = helium_exception_handler(exc, _context(client_version='3.16.14'))

        # THEN
        self.assertEqual(response.data, {
            'title': [{'message': 'This field is required.', 'code': 'required'}],
            'nested': {'start': [{'message': 'Bad.', 'code': 'required'}]},
        })

    def test_non_field_errors_with_codes(self):
        # GIVEN
        exc = ValidationError("'email' is required", code='required')

        # WHEN
        response = helium_exception_handler(exc, _context())

        # THEN
        self.assertEqual(response.data, [{'message': "'email' is required", 'code': 'required'}])

    def test_detail_for_a_legacy_app(self):
        # GIVEN
        exc = NotFound('No Course matches the given query.')

        # WHEN
        response = helium_exception_handler(exc, _context(client_version='3.16.12'))

        # THEN
        self.assertEqual(response.data, {'detail': 'No Course matches the given query.'})

    def test_detail_with_codes(self):
        for exc, code in ((NotFound('No Course matches the given query.'), 'not_found'),
                          (Http404('No Course matches the given query.'), 'not_found'),
                          (PermissionDenied('Your account is no longer active.', code='account_no_longer_active'),
                           'account_no_longer_active'),
                          (Throttled(wait=3), 'throttled')):
            with self.subTest(exc=exc):
                # WHEN
                response = helium_exception_handler(exc, _context())

                # THEN
                self.assertEqual(response.data['code'], code)
                self.assertEqual(set(response.data), {'detail', 'code'})
                self.assertIsInstance(response.data['detail'], str)

    def test_coded_bodies_pass_through_with_codes(self):
        for exc in (InvalidToken(),
                    PermissionDenied(detail={'detail': 'Not active.', 'code': 'account_inactive', 'email': 'a@b.c'}),
                    ValidationError({'error': 'invalid_request', 'error_description': 'Bad.'})):
            with self.subTest(exc=exc):
                # GIVEN
                expected = helium_exception_handler(exc, _context(client_version='3.16.12')).data

                # WHEN
                response = helium_exception_handler(exc, _context())

                # THEN
                self.assertEqual(response.data, expected)

    def test_ended_session_asks_to_sign_in_again(self):
        for exc, code in ((InvalidToken('Token is expired'), 'token_not_valid'),
                          (NotAuthenticated(), 'not_authenticated')):
            with self.subTest(exc=exc):
                # WHEN
                response = helium_exception_handler(exc, _context())

                # THEN
                self.assertEqual(response.data['detail'], 'Please sign in to continue.')
                self.assertEqual(response.data['code'], code)

    def test_field_shaped_authentication_failure_with_codes(self):
        # GIVEN
        exc = AuthenticationFailed({'password': ['The password is incorrect.']}, code='password_incorrect')

        # WHEN
        response = helium_exception_handler(exc, _context())

        # THEN
        self.assertEqual(response.data,
                         {'password': [{'message': 'The password is incorrect.', 'code': 'password_incorrect'}]})
