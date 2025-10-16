__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.12.39"

import logging

from django.conf import settings

from conf.celery import app
from helium.common.utils import metricutils
from helium.feed.services import icalexternalcalendarservice

logger = logging.getLogger(__name__)


@app.task(soft_time_limit=settings.CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT)
def reindex_feeds():
    metrics = metricutils.task_start("feed.reindex")

    icalexternalcalendarservice.reindex_stale_feed_caches()

    metricutils.task_stop(metrics)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to reindex external calendars periodically
    sender.add_periodic_task(settings.REINDEX_FEED_FREQUENCY_SEC, reindex_feeds.s())
