__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.8"

from rollbar.contrib.django.middleware import RollbarNotifierMiddleware


class HeliumRollbarMiddleware(RollbarNotifierMiddleware):
    def process_exception(self, request, exc):
        if not request.path.startswith("/status/"):
            super(HeliumRollbarMiddleware, self).process_exception(request, exc)
