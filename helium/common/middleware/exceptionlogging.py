__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.8"

from sentry_sdk import capture_exception


class HeliumSentryMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exc):
        if not request.path.startswith("/status/"):
            capture_exception(exc)
