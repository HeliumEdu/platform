__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import SimpleTestCase

from helium.common.utils.versionutils import client_version_gte, get_client_version


def _request_with_header(header):
    request = mock.Mock()
    request.headers = {'X-Client-Version': header} if header is not None else {}
    return request


class TestCaseVersionUtils(SimpleTestCase):
    def test_get_client_version_parses_valid_header(self):
        # GIVEN
        request = _request_with_header('3.8.0')

        # WHEN
        version = get_client_version(request)

        # THEN
        self.assertEqual(version, (3, 8, 0))

    def test_get_client_version_parses_header_with_build_suffix(self):
        # GIVEN
        request = _request_with_header('3.8.0+345')

        # WHEN
        version = get_client_version(request)

        # THEN
        self.assertEqual(version, (3, 8, 0))

    def test_get_client_version_returns_none_for_absent_header(self):
        # GIVEN
        request = _request_with_header(None)

        # WHEN
        version = get_client_version(request)

        # THEN
        self.assertIsNone(version)

    def test_get_client_version_returns_none_for_malformed_header(self):
        # GIVEN
        request = _request_with_header('not-a-version')

        # WHEN
        version = get_client_version(request)

        # THEN
        self.assertIsNone(version)

    def test_get_client_version_returns_none_for_none_request(self):
        # GIVEN/WHEN
        version = get_client_version(None)

        # THEN
        self.assertIsNone(version)

    def test_client_version_gte_true_when_equal(self):
        # GIVEN
        request = _request_with_header('3.8.0')

        # WHEN/THEN
        self.assertTrue(client_version_gte(request, '3.8.0'))

    def test_client_version_gte_true_when_above(self):
        # GIVEN
        request = _request_with_header('3.9.0')

        # WHEN/THEN
        self.assertTrue(client_version_gte(request, '3.8.0'))

    def test_client_version_gte_false_when_below(self):
        # GIVEN
        request = _request_with_header('3.7.3')

        # WHEN/THEN
        self.assertFalse(client_version_gte(request, '3.8.0'))

    def test_client_version_gte_false_when_header_absent(self):
        # GIVEN
        request = _request_with_header(None)

        # WHEN/THEN
        self.assertFalse(client_version_gte(request, '3.8.0'))

    def test_client_version_gte_false_when_request_is_none(self):
        # GIVEN/WHEN/THEN
        self.assertFalse(client_version_gte(None, '3.8.0'))

    def test_client_version_gte_raises_for_invalid_min_version(self):
        # GIVEN
        request = _request_with_header('3.8.0')

        # WHEN/THEN
        with self.assertRaises(ValueError):
            client_version_gte(request, 'not-a-version')
