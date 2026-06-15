__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework.throttling import AnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class PerEmailThrottle(AnonRateThrottle):
    """
    Base throttle that keys on the submitted email address rather than IP. Subclasses
    must set ``scope`` to a value registered in ``DEFAULT_THROTTLE_RATES``.

    Falls back to no throttling (returns ``None`` cache key) when no email is present,
    allowing the global ``AnonRateThrottle`` to handle that case.
    """

    def get_cache_key(self, request, view):
        email = (
            request.data.get('email') or request.GET.get('email') or ''
        ).lower().strip()
        if not email:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': email}


class ForgotPasswordEmailThrottle(PerEmailThrottle):
    """
    Rate throttle for the forgot-password endpoint, keyed per submitted email.
    """
    scope = 'forgot_password_email'


class ResendVerificationEmailThrottle(PerEmailThrottle):
    """
    Rate throttle for the resend-verification endpoint, keyed per submitted email.
    """
    scope = 'resend_verification_email'


class SESWebhookThrottle(AnonRateThrottle):
    """
    Rate throttle for the SES/SNS webhook endpoint. SNS delivers serially to a single
    HTTP subscription (one message, wait for 2xx, next message), so legitimate volume
    is bounded by email send rate — well under 60/min for this platform. 60/min gives
    headroom for retry bursts while blocking unauthenticated hammering.
    """
    scope = 'ses_webhook'


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
            logger.info(
                f'support contact submission rejected (ip={self.get_ident(request)})'
            )
        return allowed


class UserTokenRateThrottle(DRFUserRateThrottle):
    """
    Tight rate throttle for the API token management endpoint; rotations should be rare.
    """
    scope = 'user_token'


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
