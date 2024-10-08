from urllib.parse import urlparse


def strip_scheme(url):
    """
    Return the URI with the scheme stripped.

    :param url: The URI to strip.
    :return: The stripped URI.
    """
    parsed = urlparse(url)
    scheme = "%s://" % parsed.scheme
    return parsed.geturl().replace(scheme, '', 1)
