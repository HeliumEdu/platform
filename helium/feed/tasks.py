__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings

from conf.celery import app
from helium.common.periodic import register_periodic
from helium.common.utils import metricutils
from helium.feed.services import icalexternalcalendarservice

logger = logging.getLogger(__name__)


@app.task(bind=True, soft_time_limit=settings.CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT)
def reindex_feeds(self, calendar_ids=None):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("feed.reindex", priority="low", published_at_ms=published_at_ms)

    icalexternalcalendarservice.reindex_stale_feed_caches(calendar_ids=calendar_ids)

    metricutils.task_stop(metrics)


register_periodic(reindex_feeds, settings.REINDEX_FEED_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
