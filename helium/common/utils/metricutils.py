__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.34"

import logging
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

from datadog import initialize, statsd

initialize(statsd_host=settings.DATADOG_STATSD_HOST)

DATADOG_METRICS = True
DATADOG_BASE_TAGS = [f"version:{settings.PROJECT_VERSION}", f"env:{settings.ENVIRONMENT}"]


def increment(metric, request=None, response=None, value=1, extra_tags=None):
    tags = DATADOG_BASE_TAGS.copy() + extra_tags if extra_tags else []

    if request:
        tags.extend(
            [f"method:{request.method}", f"authenticated:{str(request.user.is_authenticated).lower()}"])
        if request.user.is_authenticated:
            tags.append(f"staff:{str(request.user.is_staff).lower()}")
        if 'User-Agent' in request.headers:
            tags.append(f"user-agent:{request.headers.get('User-Agent')}")
    if response:
        tags.append(f"status_code:{response.status_code}")

    logger.warning(f"EMIT METRIC {metric} WITH {tags}")

    statsd.increment(f"platform.{metric}", value=value, tags=tags)


def request_start(request):
    metric_id = f"platform.request.{re.sub('[^a-zA-Z]+', '', request.path)}"

    return {
        'Request-Metric-ID': metric_id,
        'Request-Metric-Start': int(round(time.time() * 1000)),
        'Request-Method': request.method
    }


def request_stop(metrics, response):
    metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Request-Metric-Start']

    increment(metrics['Request-Metric-ID'], response=response,
              extra_tags=[f"method:{metrics['Request-Method']}"])
    statsd.timing(metrics['Request-Metric-ID'] + ".time", metrics['Request-Metric-Millis'], tags=DATADOG_BASE_TAGS)

    metrics.pop('Request-Method', None)
    for name, value in metrics.items():
        response.headers[name] = (name, str(value))


def task_start(task_name):
    metric_id = f"platform.task.{task_name}"

    return {
        'Task-Metric-ID': metric_id,
        'Task-Metric-Start': int(round(time.time() * 1000))
    }


def task_stop(metrics):
    metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Task-Metric-Start']

    increment(metrics['Task-Metric-ID'])
    statsd.timing(metrics['Task-Metric-ID'] + ".time", metrics['Request-Metric-Millis'], tags=DATADOG_BASE_TAGS)
