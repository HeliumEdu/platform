__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken


class OutstandingTokenProxy(OutstandingToken):
    class Meta:
        proxy = True
        app_label = 'helium_auth'
        verbose_name = 'Token (outstanding)'
        verbose_name_plural = 'Tokens (outstanding)'


class BlacklistedTokenProxy(BlacklistedToken):
    class Meta:
        proxy = True
        app_label = 'helium_auth'
        verbose_name = 'Token (blacklist)'
        verbose_name_plural = 'Tokens (blacklist)'
