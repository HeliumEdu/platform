import logging

from helium.auth.models import UserPushToken
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


def revoke_push_tokens(users) -> int:
    """
    Retire the push registrations for the given users.

    Pair this with anything that revokes a session server-side. A client that signs itself out
    deletes its own registration, but one revoked from the server can no longer authenticate that
    request, so its device would keep receiving reminders it cannot open.

    :param users: a queryset or iterable of users, or of user ids.
    :return: the number of push tokens deleted.
    """
    deleted, _ = UserPushToken.objects.filter(user__in=users).delete()

    if deleted:
        logger.info(f'Revoked {deleted} push token(s) alongside session revocation')
        metricutils.increment('action.push.token.revoked', value=deleted)

    return deleted
