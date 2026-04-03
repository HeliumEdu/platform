__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import re
from random import randint

from django.conf import settings
from django.contrib.auth import get_user_model


def is_admin_allowed_email(email):
    """
    Return True if the email's domain is in ADMIN_ALLOWED_DOMAINS.
    """
    domain = email.split('@')[-1].lower() if '@' in email else ''
    return domain in settings.ADMIN_ALLOWED_DOMAINS


def generate_verification_code():
    code = None
    while not code:
        code = randint(100000, 999999)

    return code


def generate_unique_username_from_email(email):
    """
    Generate a unique username from an email local-part, appending a counter on collisions.
    """
    UserModel = get_user_model()

    max_length = UserModel._meta.get_field('username').max_length

    local_part = (email or '').split('@', 1)[0].strip().lower()
    base_username = re.sub(r'[^\w.+-]', '', local_part) or 'user'
    base_username = base_username[:max_length]

    username = base_username
    counter = 1

    while UserModel.objects.filter(username=username).exists():
        suffix = str(counter)
        truncated_base = base_username[:max_length - len(suffix)]
        username = f'{truncated_base}{suffix}'
        counter += 1

    return username
