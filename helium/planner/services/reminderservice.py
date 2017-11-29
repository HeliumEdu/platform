"""
Service for interacting with reminders.
"""

import logging

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def find_by_user(user):
    logger.debug('Finding reminders for user %d', user.pk)

    reminders_count = 0
    if hasattr(user, 'reminders_count'):
        # TODO: not yet implemented
        reminders_count = 0

    return reminders_count
