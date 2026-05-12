__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from rest_framework.throttling import AnonRateThrottle


class DeleteInactiveUserThrottle(AnonRateThrottle):
    """
    Stricter anonymous throttle for the delete-inactive-user endpoint to limit
    its use as a password-guessing vector against unverified accounts.
    """
    scope = 'delete_inactive'
