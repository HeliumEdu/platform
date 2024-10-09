from urllib.parse import urlparse, urlunparse


def strip_scheme(url):
    """
    Return the URI with the scheme stripped.

    :param url: The URI to strip.
    :return: The stripped URI.
    """
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1)


def strip_www(url):
    """
    Return a URI prefixed with www.

    :param url: The URI to prepend.
    :return: THe prepended URI.
    """
    parsed = urlparse(url)
    if parsed.netloc.startswith('www.'):
        netloc = parsed.netloc.removeprefix('www.')
        parsed = parsed._replace(netloc=netloc)
    return urlunparse(parsed)
