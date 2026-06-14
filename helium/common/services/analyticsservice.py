__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

from helium.auth.utils.userutils import is_staff_user
from helium.common.utils import metricutils
from helium.common.utils.httputils import urlopen_secure

logger = logging.getLogger(__name__)

GA4_COLLECT_URL = 'https://www.google-analytics.com/mp/collect'
GA4_REQUEST_TIMEOUT_SECONDS = 5


def _should_emit(user):
    """
    Return False if analytics emission should be skipped for this user (staff / missing config).
    """
    if not getattr(settings, 'GA4_MEASUREMENT_ID', None) or not getattr(settings, 'GA4_API_SECRET', None):
        return False

    if is_staff_user(user):
        return False

    return True


def send_event(user, name, params=None, user_properties=None):
    """
    Emit a GA4 event via the Measurement Protocol v2 for the given user. Best-effort: logs and
    swallows failures so callers never block on analytics delivery.

    :param user: The [User] the event is attributed to. `user.pk` is used for both `client_id`
                 (as `server-<pk>`) and GA4 `user_id` so events join the user's existing profile
                 without a real App Instance ID.
    :param name: The GA4 event name (e.g. `helium_onboarding_complete`).
    :param params: Optional dict of event parameters.
    :param user_properties: Optional dict of GA4 user properties to set on the user profile.
    """
    if not _should_emit(user):
        return

    payload = {
        'client_id': f'server-{user.pk}',
        'user_id': str(user.pk),
        'events': [{
            'name': name,
            'params': params or {},
        }],
    }

    if user_properties:
        payload['user_properties'] = {k: {'value': v} for k, v in user_properties.items()}

    query = urllib.parse.urlencode({
        'measurement_id': settings.GA4_MEASUREMENT_ID,
        'api_secret': settings.GA4_API_SECRET,
    })
    url = f'{GA4_COLLECT_URL}?{query}'

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'},
        method='POST',
    )

    try:
        with urlopen_secure(request, timeout=GA4_REQUEST_TIMEOUT_SECONDS) as response:
            # GA4 MP returns 204 on success; anything else is suspicious but non-fatal.
            if response.status != 204:
                logger.warning(f'GA4 MP returned unexpected status {response.status} for event {name}')
                metricutils.increment('action.analytics.unexpected_status')
                return

        metricutils.increment('action.analytics.sent')
    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning(f'Failed to send GA4 event {name}: {e}')
        metricutils.increment('action.analytics.failed')
    except Exception:
        logger.error(f'Unexpected error sending GA4 event {name}', exc_info=True)
        metricutils.increment('action.analytics.failed')
