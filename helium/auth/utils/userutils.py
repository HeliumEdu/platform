__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import re
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model


def is_admin_allowed_email(email):
    """
    Return True if the email's domain is in ADMIN_ALLOWED_DOMAINS. Security boundary — governs
    who can be promoted to superuser. Not the right predicate for filtering internal staff out
    of analytics/metrics; use `is_staff_user` for that.
    """
    domain = email.split('@')[-1].lower() if '@' in email else ''
    return domain in settings.ADMIN_ALLOWED_DOMAINS


def is_staff_email(email):
    """
    Return True if the email belongs to a staff domain. Matches the frontend's `setStaffStatus`
    filter. Use when a User object isn't available (e.g. bounce handling with just an address).
    """
    lowered = (email or '').lower()
    domain = lowered.split('@')[-1] if '@' in lowered else ''
    return domain == 'heliumedu.com' or domain.endswith('.heliumedu.com') or \
           domain == 'heliumedu.dev' or domain.endswith('.heliumedu.dev')


def is_staff_user(user):
    """
    Return True if the user is internal staff — superuser or has a staff email domain. Matches
    the admin-area `staff_filter` predicate, so the same users are excluded from analytics and
    metrics across the stack.
    """
    if user is None:
        return False
    if user.is_superuser:
        return True
    return is_staff_email(user.email)


def generate_verification_code():
    return secrets.randbelow(900000) + 100000


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
