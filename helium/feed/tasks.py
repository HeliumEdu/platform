__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.conf import settings

from conf.celery import app
from helium.common.utils import metricutils
from helium.feed.services import icalexternalcalendarservice

logger = logging.getLogger(__name__)


@app.task(soft_time_limit=settings.CELERY_TASK_CALENDAR_SYNC_SOFT_TIME_LIMIT)
def reindex_external_calendars():
    metrics = metricutils.task_start("reindex_external_calendars")

    icalexternalcalendarservice.reindex_stale_caches()

    # A metrics monitor should exist for this, average runtime should not exceed EXTERNAL_CALENDAR_REINDEX_FREQUENCY_SEC
    metricutils.task_stop(metrics)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to reindex external calendars periodically
    sender.add_periodic_task(settings.EXTERNAL_CALENDAR_REINDEX_FREQUENCY_SEC, reindex_external_calendars.s())
