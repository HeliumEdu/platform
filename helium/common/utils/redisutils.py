from typing import Dict

import redis
from django.conf import settings
from kombu.transport.redis import Channel

_redis_client = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.CELERY_BROKER_URL)
    return _redis_client


def get_celery_queue_depths(queue: str = 'celery') -> Dict[str, int]:
    """
    Count the tasks waiting in the broker, split by priority.

    The broker keeps one list per priority step, so a single list length misses every other priority.
    `high` is the `CELERY_PRIORITY_HIGH` list (also where tasks dispatched without a priority land);
    `low` is every other step combined.

    :param queue: The Celery queue name
    :return: A dict with `high` and `low` counts
    """
    priority_steps = settings.CELERY_BROKER_TRANSPORT_OPTIONS['priority_steps']

    pipe = get_redis_client().pipeline()
    for step in priority_steps:
        pipe.llen(_priority_list_key(queue, step))
    sizes = dict(zip(priority_steps, pipe.execute()))

    high = sizes.pop(settings.CELERY_PRIORITY_HIGH)
    return {'high': high, 'low': sum(sizes.values())}


def _priority_list_key(queue, step):
    return f"{queue}{Channel.sep}{step}" if step else queue
