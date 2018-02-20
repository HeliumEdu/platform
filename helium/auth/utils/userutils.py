from random import randint

from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'


def generate_phone_verification_code():
    code = None
    while not code:
        code = randint(100000, 999999)

        # Ensure the slug does not already exist in the database
        if get_user_model().objects.phone_verification_code_used(code):
            code = None

    return code


def validate_password(password):
    if not password or len(password) < 8:
        return "Your password must be at least 8 characters long and contain one letter and one number."

    first_isalpha = password[0].isalpha()
    if all(c.isalpha() == first_isalpha for c in password):
        return "Your password must be at least 8 characters long and contain one letter and one number."


def is_staff(user):
    return user.is_staff


def is_anonymous(user):
    return not user.is_authenticated()
