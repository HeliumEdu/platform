"""
Utility functions.
"""

import datetime
import hashlib
import sys
from random import randint

import requests
from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'


def get_status_code(url, allow_redirects=False):
    response = requests.head(url, allow_redirects=allow_redirects)

    return response.status_code


def remove_non_alnum(dirty_str):
    return unicode(''.join(e for e in dirty_str.lower() if e.isalnum()))


def generate_verification_code():
    code = None
    while not code:
        seed_text = randint(0, sys.maxint)

        code = hashlib.sha1(str(seed_text) + datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')).hexdigest()
        # Ensure the slug does not already exist in the database
        if get_user_model().objects.filter(verification_code=code).exists():
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
