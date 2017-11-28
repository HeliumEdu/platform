"""
Utility functions.
"""

import datetime
import hashlib
import sys
from random import randint, choice

from django.conf import settings
from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def generate_random_color(used=()):
    color = choice(settings.ALLOWED_COLORS)
    # Once we've used all allowed colors, we have to duplicate, but until then try to be unique
    if len(used) < len(settings.ALLOWED_COLORS):
        while color in used:
            color = choice(settings.ALLOWED_COLORS)
    return color


def generate_verification_code():
    code = None
    while not code:
        seed_text = randint(0, sys.maxint)

        code = hashlib.sha1(str(seed_text) + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')).hexdigest()
        # Ensure the slug does not already exist in the database
        if get_user_model().objects.filter(verification_code=code).exists():
            code = None

    return code


def generate_phone_verification_code():
    code = None
    while not code:
        code = randint(100000, 999999)

        # Ensure the slug does not already exist in the database
        if get_user_model().objects.filter(profile__phone_verification_code=code).exists():
            code = None

    return code


def is_password_valid(password):
    valid = True

    if len(password) < 8:
        valid = False

    first_isalpha = password[0].isalpha()
    if all(c.isalpha() == first_isalpha for c in password):
        valid = False

    return valid
