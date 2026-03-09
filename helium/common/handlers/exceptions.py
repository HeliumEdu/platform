__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def helium_exception_handler(exc, context):
    if isinstance(exc, Throttled):
        wait = round(exc.wait) if exc.wait is not None else None
        if wait is not None:
            exc.detail = f"Request was throttled. Try again in {wait} second{'s' if wait != 1 else ''}."
        else:
            exc.detail = "Request was throttled. Try again later."

    return exception_handler(exc, context)
