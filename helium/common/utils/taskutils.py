import logging
from typing import Optional

from celery import Task
from django.conf import settings
from django.db import OperationalError as DatabaseOperationalError
from kombu.exceptions import OperationalError

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class MetricsTask(Task):
    """
    Base for every task, reporting a failure metric when one raises.

    The failing task's own metrics, stashed by :func:`metricutils.task_start`, name the metric, so
    a failure is reported under the same name the body reports its successes under.

    Those metrics live in the worker's memory, so a task killed outright leaves none behind to
    report against. That case is counted separately as `task.lost`, under the Celery task name.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        metrics = getattr(self.request, 'helium_metrics', None)

        if not metrics:
            metricutils.increment('task.lost', extra_tags=[f'name:{self.name}'])
            return

        metricutils.task_failure(metrics['Task-Metric-ID'],
                                 exception_type=type(exc).__name__,
                                 priority=metrics.get('Task-Metric-Priority', 'low'),
                                 metrics=metrics)


def retry_on_db_error(ex, metrics, task, args, retries, kwargs=None):
    """
    Reschedule `task` after a transient DB error, or re-raise once retries are exhausted or the
    error isn't retryable. Contending tasks can deadlock or raise an IntegrityError when they touch
    the same rows in different orders; both clear on a delayed retry.
    """
    non_retryable = (isinstance(ex, DatabaseOperationalError)
                     and (not ex.args or ex.args[0] not in settings.DB_RETRYABLE_ERROR_CODES))
    if non_retryable or retries >= settings.DB_INTEGRITY_RETRIES:
        raise ex

    logger.warning(f"Retryable database error occurred, delaying before retrying `{task.name}` task")
    safe_apply_async(task, args, kwargs=kwargs,
                     countdown=settings.DB_INTEGRITY_RETRY_DELAY_SECS,
                     priority=settings.CELERY_PRIORITY_LOW)
    metricutils.task_stop(metrics, value=0)


def safe_apply_async(task, args=None, kwargs=None, critical=False, **options) -> Optional[object]:
    try:
        return task.apply_async(args=args, kwargs=kwargs, **options)
    except OperationalError:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        if critical:
            metricutils.increment("task.sync_fallback", extra_tags=[f"name:{task.name}"])
            logger.info(f"Executing {task.name} synchronously as fallback")
            return task.apply(args=args, kwargs=kwargs)
        return None


def safe_delay(task, *args, critical=False, **kwargs) -> Optional[object]:
    try:
        return task.delay(*args, **kwargs)
    except OperationalError:
        logger.warning(f"Failed to dispatch task {task.name}, broker may be unavailable",
                       exc_info=True)
        if critical:
            metricutils.increment("task.sync_fallback", extra_tags=[f"name:{task.name}"])
            logger.info(f"Executing {task.name} synchronously as fallback")
            return task.apply(args=args, kwargs=kwargs)
        return None
