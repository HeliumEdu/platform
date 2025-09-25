import re

from django.utils.deprecation import MiddlewareMixin

from helium.common.utils import metricutils


class InternalServerErrorMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        metric_id = f"request.{re.sub('[^a-zA-Z]+', '', request.path)}"

        metricutils.increment(metric_id, request,
                              extra_tags=[f"status_code:500"])

        return None
