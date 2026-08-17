__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import contextvars
import re
import uuid
from typing import Optional

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'request_id', default=None
)


def sanitize_request_id(value: Optional[str]) -> str:
    """Return a trusted request id for the current request.

    A client-supplied value is accepted only if it is a well-formed UUID;
    otherwise a fresh one is generated. Validating (rather than trusting the
    header verbatim) prevents log injection from a crafted header value.

    :param value: The raw ``X-Request-ID`` header value, or None if absent.
    :return: A well-formed UUID string, either the sanitized client value or a
        newly generated one.
    """
    if value:
        candidate = value.strip()
        if _UUID_RE.match(candidate):
            return candidate.lower()
    return str(uuid.uuid4())


def set_request_id(value: str) -> "contextvars.Token[Optional[str]]":
    """Bind the request id to the current context.

    :param value: The request id to bind.
    :return: A reset token to pass to :func:`reset_request_id`.
    """
    return _request_id_var.set(value)


def get_request_id() -> Optional[str]:
    """Return the request id bound to the current context.

    :return: The bound request id, or None outside of a request (e.g. Celery
        tasks, management commands, startup).
    """
    return _request_id_var.get()


def reset_request_id(token: "contextvars.Token[Optional[str]]") -> None:
    """Unbind the request id from the current context.

    :param token: The reset token returned by :func:`set_request_id`.
    """
    _request_id_var.reset(token)
