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
