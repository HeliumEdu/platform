__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from helium.common.utils import metricutils


class HeliumExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return response

    def process_exception(self, request, exc):
        metric_id = metricutils.path_to_metric_id(request.path)

        metricutils.increment('request', request=request,
                              extra_tags=[f"path:{metric_id}", "status_code:500"])

        return None
