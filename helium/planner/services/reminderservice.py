"""
Service for interacting with reminders.
"""

import logging

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def find_by_user(user):
    reminders_count = 0
    if hasattr(user, 'reminders_count'):
        # TODO: not yet implemented (and this service may be removed in favor of directly accessing the Manager once reminders are implemented)
        reminders_count = 0

    logger.debug('User {} has {} reminders'.format(user.get_username(), reminders_count))

    return reminders_count
