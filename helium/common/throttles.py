__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle


class DeleteInactiveUserThrottle(AnonRateThrottle):
    """
    Stricter anonymous throttle for the delete-inactive-user endpoint to limit
    its use as a password-guessing vector against unverified accounts.
    """
    scope = 'delete_inactive'


class SupportContactThrottle(AnonRateThrottle):
    """
    Throttle for the public support contact endpoint. Slower than the
    default anonymous rate so the form can't be abused as a high-volume relay
    into the JSM email inbox.
    """
    scope = 'support_contact'


class UserRateThrottle(DRFUserRateThrottle):
    """
    Uses a higher rate limit for requests from the legacy frontend (www.heliumedu.com),
    which fans out more API calls per page load than the modern frontend. All other
    clients use the standard user rate.

    TODO: Remove this class and restore rest_framework.throttling.UserRateThrottle in
    DEFAULT_THROTTLE_CLASSES once the legacy frontend is retired.
    """

    def _is_legacy_frontend(self, origin):
        # Production legacy frontend
        if origin.startswith('https://www.') and origin.endswith('heliumedu.com'):
            return True
        # Local legacy frontend
        if origin.startswith('http://localhost:3000'):
            return True
        return False

    def allow_request(self, request, view):
        origin = request.META.get('HTTP_ORIGIN', '')
        if self._is_legacy_frontend(origin):
            self.scope = 'user_legacy'
            self.rate = self.get_rate()
            self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)
