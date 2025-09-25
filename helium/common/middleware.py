import re

from django.utils.deprecation import MiddlewareMixin

from helium.common.utils import metricutils


class InternalServerErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        metric_id = f"platform.request.{re.sub('[^a-zA-Z]+', '', request.path)}.{request.method}"
        metricutils.increment(metric_id, request)
        return None

    def process_response(self, request, response):
        if response.status_code == 500:
            metricutils.increment("500", request)
        return response
