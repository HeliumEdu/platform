__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

from random import randint


def generate_verification_code():
    code = None
    while not code:
        code = randint(100000, 999999)

    return code
