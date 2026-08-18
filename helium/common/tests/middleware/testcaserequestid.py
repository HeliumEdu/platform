import re
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from helium.common.filters import RequestIDFilter
from helium.common.middleware.requestid import RequestIDMiddleware
from helium.common.utils.requestid import get_request_id

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
)


def _middleware(captured=None):
    """Build the middleware with a get_response that records the in-request
    request id (via `captured`) and returns a real HttpResponse."""

    def get_response(request):
        if captured is not None:
            captured['request_id'] = get_request_id()
            captured['on_request'] = getattr(request, 'request_id', None)
        return HttpResponse('ok')

    return RequestIDMiddleware(get_response)


class TestCaseRequestID(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_generates_id_when_header_absent(self):
        # GIVEN
        request = self.factory.get('/api/planner/courses/')
        captured = {}
        middleware = _middleware(captured)

        # WHEN
        response = middleware(request)

        # THEN
        self.assertIsNotNone(captured['request_id'])
        self.assertTrue(_UUID_RE.match(captured['request_id']))
        self.assertEqual(response['X-Request-ID'], captured['request_id'])

    def test_preserves_valid_client_uuid(self):
        # GIVEN
        client_id = '3f1a2b4c-5d6e-4f80-9a1b-2c3d4e5f6071'
        request = self.factory.get(
            '/api/planner/courses/', HTTP_X_REQUEST_ID=client_id
        )
        captured = {}
        middleware = _middleware(captured)

        # WHEN
        response = middleware(request)

        # THEN
        self.assertEqual(captured['request_id'], client_id)
        self.assertEqual(response['X-Request-ID'], client_id)

    def test_regenerates_when_client_id_malformed(self):
        # GIVEN
        request = self.factory.get(
            '/api/planner/courses/',
            HTTP_X_REQUEST_ID='not-a-uuid\n[FORGED] INFO fake log line',
        )
        captured = {}
        middleware = _middleware(captured)

        # WHEN
        response = middleware(request)

        # THEN
        self.assertTrue(_UUID_RE.match(captured['request_id']))
        self.assertNotIn('FORGED', captured['request_id'])
        self.assertEqual(response['X-Request-ID'], captured['request_id'])

    def test_binds_request_attribute(self):
        # GIVEN
        request = self.factory.get('/api/planner/courses/')
        captured = {}
        middleware = _middleware(captured)

        # WHEN
        middleware(request)

        # THEN
        self.assertEqual(captured['on_request'], captured['request_id'])

    def test_context_var_reset_after_request(self):
        # GIVEN
        request = self.factory.get('/api/planner/courses/')
        middleware = _middleware()

        # WHEN
        middleware(request)

        # THEN
        self.assertIsNone(get_request_id())

    def test_context_var_reset_even_when_view_raises(self):
        # GIVEN
        def get_response(request):
            raise ValueError('boom')

        middleware = RequestIDMiddleware(get_response)
        request = self.factory.get('/api/planner/courses/')

        # WHEN
        with self.assertRaises(ValueError):
            middleware(request)

        # THEN
        self.assertIsNone(get_request_id())

    def test_filter_defaults_to_dash_outside_request(self):
        # GIVEN
        record = mock.MagicMock()
        log_filter = RequestIDFilter()

        # WHEN
        result = log_filter.filter(record)

        # THEN
        self.assertTrue(result)
        self.assertEqual(record.request_id, '-')
