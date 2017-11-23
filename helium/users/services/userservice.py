"""
User functions.
"""

import logging

from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


def find_by_id(user_id):
    return get_user_model().objects.get(id=user_id)
