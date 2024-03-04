__copyright__ = "Copyright 2018, Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

from random import randint

from django.contrib.auth import get_user_model


def generate_phone_verification_code():
    code = None
    while not code:
        code = randint(100000, 999999)

        # Ensure the slug does not already exist in the database
        if get_user_model().objects.phone_verification_code_used(code):
            code = None

    return code
