__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.49"

import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

from datadog import initialize, statsd

initialize(statsd_host=settings.DATADOG_STATSD_HOST)

DATADOG_METRICS = True
DATADOG_BASE_TAGS = [f"version:{settings.PROJECT_VERSION}", f"env:{settings.ENVIRONMENT}"]


def increment(metric, request=None, response=None, user=None, value=1, extra_tags=None):
    if user:
        user = user
    elif request and hasattr(request, 'context'):
        user = request.context.get('user', None)
    else:
        user = None

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
                tags.append(f"user_agent:{request.headers.get('User-Agent')}")
        if response:
            tags.append(f"status_code:{response.status_code}")

        metric_id = f"platform.{metric}"
        statsd.increment(metric_id, value=value, tags=tags)

        logger.debug(f"Metric: {metric_id} incremented {value}, with tags {tags}")
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def timing(metric, value, extra_tags=None):
    try:
        tags = DATADOG_BASE_TAGS.copy() + (extra_tags if extra_tags else [])

        metric_id = f"platform.{metric}"
        statsd.timing(metric_id, value=value, tags=tags)
        logger.debug(f"Metric: {metric_id} took {value}ms, emitted with tags {tags}")
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def request_start(request):
    try:
        metric_id = f"request{re.sub('[^a-zA-Z.]+', '', request.path.replace('/', '.'))}".rstrip(".")

        return {
            'Request-Metric-ID': metric_id,
            'Request-Metric-Start': int(round(time.time() * 1000))
        }
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def request_stop(metrics, request, response):
    try:
        metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Request-Metric-Start']

        increment(metrics['Request-Metric-ID'], request=request, response=response)
        timing(metrics['Request-Metric-ID'], metrics['Request-Metric-Millis'])

        for name, value in metrics.items():
            response.headers[name] = (name, str(value))
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def task_start(task_name):
    try:
        metric_id = f"task.{task_name}"

        return {
            'Task-Metric-ID': metric_id,
            'Task-Metric-Start': int(round(time.time() * 1000))
        }
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)


def task_stop(metrics):
    try:
        metrics['Task-Metric-Millis'] = int(time.time() * 1000) - metrics['Task-Metric-Start']

        increment(metrics['Task-Metric-ID'])
        timing(metrics['Task-Metric-ID'], metrics['Task-Metric-Millis'])
    except Exception as e:
        logger.error("An error occurred while emitting metrics", exc_info=True)
