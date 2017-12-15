"""
Unauthenticated feed URLs (which rely on the private slug in the URL as their authentication.
"""

import logging

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def feed_ical(request, id):
    # TODO: not yet implemented, as the slugs rely on not-yet-implemented models in the "planner" app
    pass
