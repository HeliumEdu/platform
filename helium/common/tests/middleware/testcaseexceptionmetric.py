__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from unittest import mock

from django.test import TestCase, RequestFactory

from helium.common.middleware.exceptionmetric import HeliumExceptionMiddleware


class TestCaseExceptionMetric(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_middleware_call(self):
        # GIVEN
        request = self.factory.get('/api/planner/courses/')
        get_response = mock.MagicMock(return_value='response')
        middleware = HeliumExceptionMiddleware(get_response)

        # WHEN
        response = middleware(request)

        # THEN
        get_response.assert_called_once_with(request)
        self.assertEqual(response, 'response')

    @mock.patch('helium.common.middleware.exceptionmetric.metricutils.increment')
    @mock.patch('helium.common.middleware.exceptionmetric.metricutils.path_to_metric_id')
    def test_process_exception(self, mock_path_to_metric, mock_increment):
        # GIVEN
        request = self.factory.get('/api/planner/courses/')
        get_response = mock.MagicMock()
        middleware = HeliumExceptionMiddleware(get_response)
        mock_path_to_metric.return_value = 'api.planner.courses'
        exc = Exception('Test error')

        # WHEN
        result = middleware.process_exception(request, exc)

        # THEN
        mock_path_to_metric.assert_called_once_with('/api/planner/courses/')
        mock_increment.assert_called_once_with(
            'request',
            request=request,
            extra_tags=['path:api.planner.courses', 'status_code:500']
        )
        self.assertIsNone(result)
