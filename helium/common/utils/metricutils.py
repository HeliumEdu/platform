__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.34"

import re
import time

from django.conf import settings

DATADOG_METRICS = False
DATADOG_TAGS = None
if settings.DATADOG_API_KEY:
    from datadog import initialize

    options = {
        'api_key': settings.DATADOG_API_KEY,
        'app_key': settings.DATADOG_APP_KEY
    }

    initialize(**options)

    DATADOG_METRICS = True
    DATADOG_BASE_TAGS = [f"version:{settings.PROJECT_VERSION}", f"env:{settings.ENVIRONMENT}"]

from datadog import statsd


def increment(metric, request=None, response=None, value=1, extra_tags=None):
    if DATADOG_METRICS:
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

        statsd.increment(f"platform.{metric}", value=value, tags=tags)


def request_start(request):
    metric_id = f"platform.request.{re.sub('[^a-zA-Z]+', '', request.path)}"

    return {
        'Request-Metric-ID': metric_id,
        'Request-Metric-Start': int(round(time.time() * 1000)),
        'Request-Method': request.method
    }


def request_stop(metrics, response):
    if DATADOG_METRICS:
        metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Request-Metric-Start']

        increment(metrics['Request-Metric-ID'], response=response,
                  extra_tags=[f"method:{metrics['Request-Method']}"])
        statsd.timing(metrics['Request-Metric-ID'] + ".time", metrics['Request-Metric-Millis'], tags=DATADOG_TAGS)

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
    if DATADOG_METRICS:
        metrics['Task-Timer'].stop()
        metrics['Request-Metric-Millis'] = int(time.time() * 1000) - metrics['Task-Metric-Start']

        increment(metrics['Task-Metric-ID'])
        statsd.timing(metrics['Task-Metric-ID'] + ".time", metrics['Request-Metric-Millis'], tags=DATADOG_TAGS)
