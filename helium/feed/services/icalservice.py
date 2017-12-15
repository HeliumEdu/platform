"""
Service for validating, parsing, and building ICAL files.
"""

import logging

from icalendar import Calendar
from rest_framework import status
from urllib.request import urlopen, URLError

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class ICalError(Exception):
    pass


def validate_url(url):
    try:
        response = urlopen(url)

        if response.getcode() != status.HTTP_200_OK:
            raise ICalError("The URL did not return a valid response.")

        Calendar.from_ical(response.read())
    except URLError as ex:
        logger.info("The URL is not reachable: {}".format(ex.message))

        raise ICalError("The URL is not reachable.")
    except ValueError as ex:
        logger.info("The URL did not return a valid ICAL feed: {}".format(ex.message))

        raise ICalError("The URL did not return a valid ICAL feed.")
