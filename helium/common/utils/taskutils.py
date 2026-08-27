import logging
from typing import Optional

from celery import Task
from kombu.exceptions import OperationalError

from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


class MetricsTask(Task):
    """
    Base for every task, reporting a failure metric when one raises.

    The failing task's own metrics, stashed by :func:`metricutils.task_start`, name the metric, so
    a failure is reported under the same name the body reports its successes under.
    """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        metrics = getattr(self.request, 'helium_metrics', None)

        if not metrics:
            return

        metricutils.task_failure(metrics['Task-Metric-ID'],
                                 exception_type=type(exc).__name__,
                                 priority=metrics.get('Task-Metric-Priority', 'low'),
                                 metrics=metrics)


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
