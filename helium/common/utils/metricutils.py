__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.34"

import re

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
    DATADOG_TAGS = [f"version:{settings.PROJECT_VERSION}", f"env:{settings.ENVIRONMENT}"]

from datadog import statsd


def increment(metric, request=None, response=None, value=1):
    if DATADOG_METRICS:
        if request:
            DATADOG_TAGS.extend(
                [f"method:{request.method}", f"authenticated:{str(request.user.is_authenticated).lower()}"])
            if request.user.is_authenticated:
                DATADOG_TAGS.append(f"staff:{str(request.user.is_staff).lower()}")
            if 'User-Agent' in request.headers:
                DATADOG_TAGS.append(f"user-agent:{request.headers.get('User-Agent')}")
        if response:
            DATADOG_TAGS.append(f"status_code:{response.status_code}")

        statsd.increment(f"platform.{metric}", value=value, tags=DATADOG_TAGS)


def request_start(request):
    metric_id = f"platform.request.{re.sub('[^a-zA-Z]+', '', request.path)}"
    timer = statsd.histogram(metric_id, sample_rate=1)
    timer.start()

    return {
        'Request-Timer': timer,
        'Request-Metric-ID': metric_id,
        'Request-Metric-Start': int(round(timer._start_time * 1000)),
        'Request-Method': request.method
    }


def request_stop(metrics, response):
    if DATADOG_METRICS:
        metrics['Request-Timer'].stop()
        metrics['Request-Metric-Millis'] = metrics['Request-Timer'].ms

        increment(metrics['Request-Metric-ID'], response=response)
        increment(f"{metrics['Request-Metric-ID']}.{response.status_code}", metrics['Request-Timer'])

        statsd.timing(metrics['Request-Metric-ID'] + ".time", metrics['Request-Timer'].ms, tags=DATADOG_TAGS)
        statsd.timing(metrics['Request-Metric-ID'] + ".time", metrics['Request-Timer'].ms, tags=DATADOG_TAGS)

    metrics.pop('Request-Timer', None)
    metrics.pop('Request-Method', None)

    for name, value in metrics.items():
        response.headers[name] = (name, str(value))


def task_start(task_name):
    metric_id = f"platform.task.{task_name}"
    timer = statsd.histogram(metric_id, sample_rate=1)
    timer.start()

    return {
        'Task-Timer': timer,
        'Task-Metric-ID': metric_id,
        'Task-Metric-Start': int(round(timer._start_time * 1000))
    }


def task_stop(metrics):
    if DATADOG_METRICS:
        metrics['Task-Timer'].stop()
        metrics['Task-Metric-Millis'] = metrics['Task-Timer'].ms

        increment(metrics['Task-Metric-ID'])

        statsd.timing(metrics['Task-Metric-ID'] + ".time", metrics['Task-Timer'].ms, tags=DATADOG_TAGS)
