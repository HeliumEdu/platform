__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import time

from celery.signals import before_task_publish


@before_task_publish.connect
def add_publish_time(headers=None, **kwargs):
    """Add publish timestamp to task headers for queue wait time tracking."""
    if headers is not None:
        headers['published_at'] = time.time()
