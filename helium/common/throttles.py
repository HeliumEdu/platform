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


class UserTokenRateThrottle(DRFUserRateThrottle):
    """
    Tight rate throttle for the API token management endpoint; rotations should be rare.
    """
    scope = 'user_token'
