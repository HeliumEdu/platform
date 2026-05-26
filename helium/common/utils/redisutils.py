__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import redis
from django.conf import settings

_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    return _redis_client
