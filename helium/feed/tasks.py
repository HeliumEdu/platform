import logging

from django.conf import settings

from conf.celery import app
from helium.common.periodic import register_periodic
from helium.common.utils import metricutils, taskutils
from helium.feed.models import ExternalCalendar
from helium.feed.services import icalexternalcalendarservice

logger = logging.getLogger(__name__)


@app.task(bind=True)
def reindex_feeds(self, calendar_id=None):
    """Reindex one calendar, or queue a task for every calendar whose cache has gone stale.

    Handing the workers a calendar apiece leaves the distribution to Celery, and keeps any one
    task well inside its time limit however far the fleet grows.
    """
    published_at_ms = metricutils.get_published_at_ms(self)
    dispatching = calendar_id is None
    metrics = metricutils.task_start("feed.reindex" if dispatching else "feed.reindex.calendar",
                                     priority="low", published_at_ms=published_at_ms)

    try:
        if dispatching:
            calendar_ids = list(ExternalCalendar.objects.needs_recached().values_list('pk', flat=True))
            for stale_id in calendar_ids:
                taskutils.safe_apply_async(reindex_feeds,
                                           kwargs={'calendar_id': stale_id},
                                           priority=settings.CELERY_PRIORITY_LOW)
            count = len(calendar_ids)
            logger.info(f"Queued {count} stale calendar(s) for reindexing")
        else:
            icalexternalcalendarservice.reindex_stale_feed_caches(calendar_ids=[calendar_id])
            count = 1
    except Exception as e:
        logger.error(f"Failed to reindex feeds: {e}", exc_info=True)
        raise

    metricutils.task_stop(metrics, value=count)


register_periodic(reindex_feeds, settings.REINDEX_FEED_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
