__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

from datadog import initialize, statsd

initialize(statsd_host=settings.DATADOG_STATSD_HOST)

DATADOG_METRICS = True
DATADOG_BASE_TAGS = [f"version:{settings.PROJECT_VERSION}", f"env:{settings.ENVIRONMENT}"]


def _normalize_user_agent_tag(user_agent):
    if not user_agent:
        return "unknown"

    ua = user_agent.lower()

    if any(bot in ua for bot in ["bot", "spider", "crawler", "slurp", "curl", "wget", "postman"]):
        return "bot"

    if "dart" in ua or "flutter" in ua:
        return "mobile_app_flutter"

    if "iphone" in ua or "ipad" in ua or "ios" in ua:
        return "mobile_browser_ios"

    if "android" in ua:
        return "mobile_browser_android"

    if any(browser in ua for browser in ["mozilla", "chrome", "safari", "firefox", "edg", "opera"]):
        return "web_browser"

    return "other"


def increment(metric, request=None, response=None, user=None, value=1, extra_tags=None):
    if not user and request and hasattr(request, 'user'):
        user = request.user

    try:
        tags = DATADOG_BASE_TAGS.copy() + (extra_tags if extra_tags else [])

        if user:
            tags.append(f"authenticated:{str(user.is_authenticated).lower()}")
            if user.is_authenticated:
                is_staff = user.is_staff or user.email.endswith("heliumedu.com") or user.email.endswith("heliumedu.dev")
                tags.append(f"staff:{str(is_staff).lower()}")

        if request:
            tags.append(f"method:{request.method}")
            if request.headers and 'User-Agent' in request.headers:
                tags.append(f"user_agent:{_normalize_user_agent_tag(request.headers.get('User-Agent'))}")
        if response:
            tags.append(f"status_code:{response.status_code}")

        metric_id = f"platform.{metric}"
        statsd.increment(metric_id, value=value, tags=tags)

        logger.debug(f"Metric: {metric_id} incremented {value}, with tags {tags}")
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def timing(metric, value, extra_tags=None):
    try:
        tags = DATADOG_BASE_TAGS.copy() + (extra_tags if extra_tags else [])

        metric_id = f"platform.{metric}"
        statsd.timing(metric_id, value=value, tags=tags)
        logger.debug(f"Metric: {metric_id} took {value}ms, emitted with tags {tags}")
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def gauge(metric, value, extra_tags=None):
    try:
        tags = DATADOG_BASE_TAGS.copy() + (extra_tags if extra_tags else [])

        metric_id = f"platform.{metric}"
        statsd.gauge(metric_id, value=value, tags=tags)
        logger.debug(f"Metric: {metric_id} gauge set to {value}, with tags {tags}")
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def path_to_metric_id(path):
    """Convert a URL path to a normalized metric ID (e.g., /planner/reminders/ -> planner.reminders)"""
    return re.sub(r'\.{2,}', '.', re.sub('[^a-zA-Z.]+', '', path.replace('/', '.'))).strip(".")


def request_start(request):
    try:
        metric_id = path_to_metric_id(request.path)

        return {
            'Request-Metric-ID': metric_id,
            'Request-Metric-Start': int(round(time.time() * 1000))
        }
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def request_stop(metrics, request, response):
    try:
        metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Request-Metric-Start']

        increment('request', request=request, response=response, extra_tags=[f"path:{metrics['Request-Metric-ID']}"])
        timing('request.timing', metrics['Request-Metric-Millis'], extra_tags=[f"path:{metrics['Request-Metric-ID']}"])

        for name, value in metrics.items():
            response.headers[name] = value
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def task_start(task_name, priority="low", published_at_ms=None):
    try:
        metric_id = f"{task_name}"
        start_time = int(round(time.time() * 1000))

        metrics = {
            'Task-Metric-ID': metric_id,
            'Task-Metric-Start': start_time,
            'Task-Metric-Priority': priority,
        }

        # Store queue time (when published) and emit wait time metric
        if published_at_ms is not None:
            metrics['Task-Metric-Queue'] = published_at_ms
            queue_wait_ms = max(0, start_time - published_at_ms)
            timing('task.queue_time', queue_wait_ms, extra_tags=[f"name:{metric_id}", f"priority:{priority}"])

        return metrics
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def task_stop(metrics, value=1, user=None):
    try:
        metrics['Task-Metric-Millis'] = int(time.time() * 1000) - metrics['Task-Metric-Start']

        task_tags = [f"name:{metrics['Task-Metric-ID']}", f"priority:{metrics.get('Task-Metric-Priority', 'low')}"]
        increment('task', user=user, value=value, extra_tags=task_tags)
        timing('task.timing', metrics['Task-Metric-Millis'], extra_tags=task_tags)
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def task_failure(task_name, exception_type=None, priority="low"):
    try:
        tags = [f"name:{task_name}", f"priority:{priority}"]
        if exception_type:
            tags.append(f"exception:{exception_type}")

        increment('task.failed', extra_tags=tags)
    except Exception:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def get_published_at_ms(celery_task):
    """
    Get the timestamp (in ms) when a task was published to the queue.
    Uses Celery's task request headers to determine when the task was published.

    Args:
        celery_task: The Celery task instance (self in a bound task)

    Returns:
        Publish timestamp in milliseconds, or None if not available
    """
    try:
        request = celery_task.request
        if not request:
            return None

        # Headers added via apply_async(headers={...}) are in request.headers
        headers = getattr(request, 'headers', {}) or {}
        published_at = headers.get('published_at')

        if published_at:
            return int(float(published_at) * 1000)

        return None
    except Exception:
        logger.warning("Could not determine publish time", exc_info=True)
        return None
