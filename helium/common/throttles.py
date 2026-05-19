__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class DeleteInactiveUserThrottle(AnonRateThrottle):
    """
    Anonymous rate throttle for the delete-inactive-user endpoint.
    """
    scope = 'delete_inactive'


class SupportContactThrottle(AnonRateThrottle):
    """
    Rate throttle for the public support contact endpoint.
    """
    scope = 'support_contact'

    def allow_request(self, request, view):
        """
        Defer to DRF's rate-limit decision; emit a metric and a log line when the
        request is not allowed.
        """
        allowed = super().allow_request(request, view)
        if not allowed:
            metricutils.increment('action.support_contact.throttled')
            logger.warning(
                f'support contact submission rejected (ip={self.get_ident(request)})'
            )
        return allowed


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
