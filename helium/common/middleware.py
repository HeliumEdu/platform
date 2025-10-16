import re

from helium.common.utils import metricutils


class HeliumMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return response

    def process_exception(self, request, exception):
        metric_id = f"{re.sub('[^a-zA-Z]+', '', request.path)}"

        metricutils.increment('request', request=request,
                              extra_tags=[f"path:{metric_id}", "status_code:500"])

        return None
