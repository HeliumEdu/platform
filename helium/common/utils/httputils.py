__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import http.client
import ipaddress
import logging
import socket
import urllib.request
from typing import Union
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 10


def _check_ssrf(url: Union[str, Request]) -> None:
    """
    Resolve the hostname in ``url`` and raise :class:`URLError` if any resolved
    address is private, loopback, link-local, reserved, or multicast.

    :param url: A URL string or :class:`urllib.request.Request`.
    :raises URLError: If the hostname resolves to a blocked address or cannot be resolved.
    """
    raw_url = url.full_url if isinstance(url, Request) else url
    hostname = urlparse(raw_url).hostname

    if not hostname:
        raise URLError("URL has no hostname")

    try:
        for *_, sockaddr in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
                logger.warning(f"SSRF blocked: {hostname} resolves to non-public IP {ip}")
                raise URLError(f"Blocked: {hostname} resolves to non-public IP {ip}")
    except URLError:
        raise
    except OSError:
        raise URLError(f"Could not resolve hostname: {hostname}")


class _SecureRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validates the redirect target's IP before following any 3xx response."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_ssrf(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_secure_opener = urllib.request.build_opener(_SecureRedirectHandler)


def urlopen_secure(url: Union[str, Request], timeout: int = _DEFAULT_TIMEOUT_SECONDS) -> http.client.HTTPResponse:
    """
    SSRF-safe drop-in for urllib.request.urlopen.

    Validates the initial URL and re-validates the IP at every redirect hop, so
    a public-to-private redirect (e.g. attacker.com → 169.254.170.2) cannot
    bypass the check. Also normalises :class:`http.client.HTTPException`
    (including ``RemoteDisconnected``) to :class:`URLError` so callers never
    receive an unhandled 500 from non-HTTP TCP services.

    Accepts the same first argument as ``urllib.request.urlopen``: either a URL
    string or a :class:`urllib.request.Request`.

    :param url: A URL string or :class:`urllib.request.Request`.
    :param timeout: Request timeout in seconds.
    :return: The HTTP response object.
    :raises URLError: If the target resolves to a blocked IP, redirects to one,
        is unreachable, or returns a non-HTTP TCP response.
    """
    _check_ssrf(url)

    try:
        return _secure_opener.open(url, timeout=timeout)
    except http.client.HTTPException as ex:
        raise URLError(str(ex)) from ex
