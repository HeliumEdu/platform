__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import re

logger = logging.getLogger(__name__)

_VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:\+\d+)?$")


def get_client_version(request):
    """
    Parse the X-Client-Version header into a (major, minor, patch) tuple.

    Returns None if the header is absent or malformed.
    """
    header = request.headers.get("X-Client-Version")
    if not header:
        return None

    match = _VERSION_PATTERN.match(header.strip())
    if not match:
        logger.debug("Malformed X-Client-Version header: %s", header)
        return None

    return tuple(int(g) for g in match.groups())


def client_version_gte(request, min_version):
    """
    Return True if the client version is >= min_version.

    min_version should be a semver string (e.g., "3.5.0").
    Returns False if the header is absent or malformed.
    """
    client = get_client_version(request)
    if client is None:
        return False

    match = _VERSION_PATTERN.match(min_version)
    if not match:
        raise ValueError(f"Invalid min_version: {min_version}")

    target = tuple(int(g) for g in match.groups())
    return client >= target
