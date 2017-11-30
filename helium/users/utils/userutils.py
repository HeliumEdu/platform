"""
Utility function for user data.
"""

from random import randint

from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


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
