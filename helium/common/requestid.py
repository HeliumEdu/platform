__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import contextvars
import re
import uuid

_UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

_request_id_var = contextvars.ContextVar('request_id', default=None)


def sanitize_request_id(value):
    """Return a client-supplied request id only if it is a well-formed UUID;
    otherwise generate a fresh one. Validating (rather than trusting verbatim)
    prevents log injection from a crafted header."""
    if value:
        candidate = value.strip()
        if _UUID_RE.match(candidate):
            return candidate.lower()
    return str(uuid.uuid4())


def set_request_id(value):
    return _request_id_var.set(value)


def get_request_id():
    return _request_id_var.get()


def reset_request_id(token):
    _request_id_var.reset(token)
