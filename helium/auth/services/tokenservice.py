import logging

from knox.models import AuthToken
from oauth2_provider.models import get_access_token_model, get_grant_model, get_refresh_token_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def issue_session_tokens(user) -> dict[str, str]:
    """
    Issue a new JWT pair for the user, as returned by every endpoint that signs a user in.

    :param user: the user to issue tokens for.
    :return: the ``access`` and ``refresh`` tokens.
    """
    token = RefreshToken.for_user(user)

    return {
        'access': str(token.access_token),
        'refresh': str(token),
    }


def blacklist_refresh_tokens(users) -> None:
    """
    Blacklist every outstanding refresh token for the given users, so none can be refreshed again.

    :param users: a queryset or iterable of users, or of user ids.
    """
    tokens = OutstandingToken.objects.filter(user__in=users)
    for token in tokens:
        BlacklistedToken.objects.get_or_create(token=token)


def create_api_token(user) -> tuple[AuthToken, str]:
    """
    Issue the user's API token, replacing any they already have (a user has at most one).

    :param user: the user to issue the API token for.
    :return: the token's instance and its plaintext, which isn't stored and can't be shown again.
    """
    AuthToken.objects.filter(user=user).delete()
    instance, token = AuthToken.objects.create(user=user)

    logger.info(f'API token created for user {user.pk}')

    return instance, token


def revoke_api_token(user) -> None:
    """
    Revoke the user's API token, if they have one.

    :param user: the user whose API token is revoked.
    """
    deleted, _ = AuthToken.objects.filter(user=user).delete()

    if deleted:
        logger.info(f'API token revoked for user {user.pk}')


def revoke_oauth_tokens(user) -> None:
    """
    Revoke every OAuth grant the user made: their access tokens, refresh tokens, and unused authorization codes.

    :param user: the user whose grants are revoked.
    """
    get_refresh_token_model().objects.filter(user=user).delete()
    get_access_token_model().objects.filter(user=user).delete()
    get_grant_model().objects.filter(user=user).delete()


def revoke_auth_tokens(user) -> None:
    """
    Revoke the user's long-lived credentials: blacklist every outstanding refresh token, delete the API token, and
    revoke every OAuth grant.

    Call this from anything that changes a password or reserves an account for deletion. Short-lived access tokens
    aren't stored, so authentication rejects those instead (password-hash claim, pending-delete check).

    :param user: the user whose credentials are revoked.
    """
    for outstanding in OutstandingToken.objects.filter(user=user):
        try:
            RefreshToken(outstanding.token).blacklist()
        except TokenError:
            # Already expired or blacklisted — safe to ignore
            pass

    deleted, _ = AuthToken.objects.filter(user=user).delete()

    if deleted:
        logger.info(f'API token revoked for user {user.pk} alongside session revocation')

    revoke_oauth_tokens(user)
