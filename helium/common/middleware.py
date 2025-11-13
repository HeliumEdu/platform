import re

from rollbar.contrib.django.middleware import RollbarNotifierMiddleware

from helium.common.utils import metricutils


class HeliumExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        return response

    def process_exception(self, request, exc):
        metric_id = f"{re.sub('[^a-zA-Z]+', '', request.path)}"

        metricutils.increment('request', request=request,
                              extra_tags=[f"path:{metric_id}", "status_code:500"])

        return None


class HeliumRollbarMiddleware(RollbarNotifierMiddleware):
    def process_exception(self, request, exc):
        if not request.path.startswith("/status"):
            super(HeliumRollbarMiddleware, self).process_exception(request, exc)
