from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ErrorDetail, NotAuthenticated, Throttled
from rest_framework.response import Response
from rest_framework.views import exception_handler
from rest_framework_simplejwt.exceptions import InvalidToken

from helium.common.errormessages import SIGN_IN_TO_CONTINUE_MESSAGE, throttled_message
from helium.common.utils.commonutils import PreconditionFailedError
from helium.common.utils.versionutils import client_version_gte, get_client_version

_CODED_BODY_KEYS = ('code', 'error')


def wants_legacy_errors(request) -> bool:
    """
    Deprecated: Remove once all clients and MINIMUM_SUPPORTED_VERSION are at or above 3.16.14.
    """
    return (get_client_version(request) is not None
            and not client_version_gte(request, settings.LEGACY_ERROR_FORMAT_BEFORE_VERSION))


def detail_body(request, message, code) -> dict:
    """
    The `{"detail": ...}` body of an error, with its `code` alongside.
    """
    if wants_legacy_errors(request):
        return {'detail': message}
    return {'detail': message, 'code': code}


def error_body(request, data):
    """
    An error response's body, with a `code` beside each message.
    """
    if wants_legacy_errors(request):
        return data
    return _with_codes(data)


def helium_exception_handler(exc, context):
    if isinstance(exc, PreconditionFailedError):
        return Response(exc.current, status=status.HTTP_412_PRECONDITION_FAILED)

    if isinstance(exc, Throttled):
        exc.detail = ErrorDetail(throttled_message(exc.wait), code=exc.default_code)
    elif isinstance(exc, InvalidToken):
        exc.detail['detail'] = ErrorDetail(SIGN_IN_TO_CONTINUE_MESSAGE, code=exc.detail['detail'].code)
    elif isinstance(exc, NotAuthenticated):
        exc.detail = ErrorDetail(SIGN_IN_TO_CONTINUE_MESSAGE, code=exc.detail.code)

    response = exception_handler(exc, context)

    if response is not None:
        response.data = error_body(context['request'], response.data)

    return response


def _with_codes(data):
    if isinstance(data, dict) and any(key in data for key in _CODED_BODY_KEYS):
        return data
    if isinstance(data, dict) and list(data) == ['detail'] and isinstance(data['detail'], ErrorDetail):
        return {'detail': data['detail'], 'code': data['detail'].code}
    return _full_details(data)


def _full_details(detail):
    if isinstance(detail, list):
        return [_full_details(item) for item in detail]
    if isinstance(detail, dict):
        return {key: _full_details(value) for key, value in detail.items()}
    return {'message': detail, 'code': detail.code}
