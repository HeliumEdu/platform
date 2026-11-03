"""
Rate limits, grouped by intent. Each scope is a rate in ``DEFAULT_THROTTLE_RATES``:

- ``user``: per verified identity (a signed-in user, a valid refresh token's user, a private feed).
- ``anon``: per network address, for requests without a verified identity.
- ``account`` / ``account_total``: sign-in and verification attempts, per account and network address / per account.
- ``email``: anything that sends an email, per endpoint and destination address.
- ``support``: messages to Helium's support desk, per network address.
- ``credential``: credential changes, per user.

Students often share one network address (a campus, a district's content filter, a VPN), so a request is limited per
address only while Helium can't tell who it is for.
"""
import logging
from functools import cached_property

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.throttling import SimpleRateThrottle

logger = logging.getLogger(__name__)


class ThrottleSubject:
    """
    Who a request is for, as far as rate limiting can tell. One subject per request; each part is resolved on first use.
    """

    def __init__(self, request, view):
        self.request = request
        self.view = view

    @classmethod
    def of(cls, request, view):
        subject = getattr(request, 'throttle_subject', None)
        if subject is None:
            subject = cls(request, view)
            request.throttle_subject = subject
        return subject

    @cached_property
    def verified_identity(self):
        """
        The signed-in user's id, or the identity an unauthenticated view returns from ``get_throttle_identity(request)``
        once it has verified who the request is for. ``None`` when neither applies.
        """
        user = self.request.user
        if user and user.is_authenticated:
            return str(user.pk)
        resolve = getattr(self.view, 'get_throttle_identity', None)
        return resolve(self.request) if resolve else None

    @cached_property
    def email(self):
        """
        The submitted ``email``, normalized: from the query string on a GET, else from the body.
        """
        source = self.request.GET if self.request.method == 'GET' else self.request.data
        value = source.get('email') if hasattr(source, 'get') else None
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip().lower()

    @cached_property
    def delivery_address(self):
        """
        The submitted email with any subaddress (``name+tag@``) folded into its base address.
        """
        if self.email is None:
            return None
        local, at, domain = self.email.rpartition('@')
        if not at:
            return self.email
        return f"{local.split('+', 1)[0]}@{domain}"

    @cached_property
    def account(self):
        """
        The account the submitted identifier names, so every spelling of it (email, username, letter case) is one
        account; the identifier itself when it names no account.
        """
        if self.email is None:
            return None
        pk = (get_user_model().objects
              .filter(Q(email__iexact=self.email) | Q(username__iexact=self.email)
                      | Q(email_changing__iexact=self.email))
              .values_list('pk', flat=True).first())
        return f'user-{pk}' if pk else self.email

    @property
    def endpoint(self):
        match = self.request.resolver_match
        return match.url_name if match else type(self.view).__name__


class HeliumThrottle(SimpleRateThrottle):
    """
    A rate limit keyed on part of the request's :class:`ThrottleSubject`. Subclasses set ``scope`` and return the
    key from :meth:`get_ident_for`, or ``None`` to leave the request to other limits.
    """

    def get_cache_key(self, request, view):
        ident = self.get_ident_for(ThrottleSubject.of(request, view), request)
        if ident is None:
            return None
        return self.cache_format % {'scope': self.scope, 'ident': ident}

    def get_ident_for(self, subject, request):
        raise NotImplementedError


class UserThrottle(HeliumThrottle):
    """
    Per verified identity.
    """
    scope = 'user'

    def get_ident_for(self, subject, request):
        return subject.verified_identity


class AnonThrottle(HeliumThrottle):
    """
    Per network address, for requests without a verified identity. A submitted email is not a verified identity.
    """
    scope = 'anon'

    def get_ident_for(self, subject, request):
        return None if subject.verified_identity is not None else self.get_ident(request)


class AccountThrottle(HeliumThrottle):
    """
    Sign-in and verification attempts, per account and network address.
    """
    scope = 'account'

    def get_ident_for(self, subject, request):
        return f'{subject.account}:{self.get_ident(request)}' if subject.account else None


class AccountTotalThrottle(HeliumThrottle):
    """
    Sign-in and verification attempts, per account from any network address.
    """
    scope = 'account_total'

    def get_ident_for(self, subject, request):
        return subject.account


class EmailThrottle(HeliumThrottle):
    """
    Anything that sends an email, per endpoint and destination address.
    """
    scope = 'email'

    def get_ident_for(self, subject, request):
        return f'{subject.endpoint}:{subject.delivery_address}' if subject.delivery_address else None


class SupportThrottle(HeliumThrottle):
    """
    Messages to Helium's support desk, per network address.
    """
    scope = 'support'

    def get_ident_for(self, subject, request):
        return self.get_ident(request)


class CredentialThrottle(HeliumThrottle):
    """
    Credential changes, per user.
    """
    scope = 'credential'

    def get_ident_for(self, subject, request):
        return subject.verified_identity
