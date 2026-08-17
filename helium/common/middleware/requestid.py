__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from django.conf import settings

from helium.common.utils.requestid import reset_request_id, sanitize_request_id, set_request_id

REQUEST_ID_HEADER = 'X-Request-ID'


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = sanitize_request_id(request.META.get('HTTP_X_REQUEST_ID'))
        token = set_request_id(request_id)
        request.request_id = request_id

        if getattr(settings, 'SENTRY_ENABLED', False):
            import sentry_sdk

            sentry_sdk.set_tag('request_id', request_id)

        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)

        response[REQUEST_ID_HEADER] = request_id

        return response
