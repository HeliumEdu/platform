__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import os
import re

from django.conf import settings
from statsd.defaults.django import statsd

from conf.configcache import config

DATADOG_METRICS = False
DATADOG_TAGS = None
if settings.DATADOG_API_KEY:
    from datadog import initialize

    options = {
        'api_key': settings.DATADOG_API_KEY,
        'app_key': settings.DATADOG_APP_KEY
    }

    initialize(**options)

    from datadog import statsd as datadog_statsd

    DATADOG_METRICS = True
    DATADOG_TAGS = [f"env:{config('ENVIRONMENT')}"]


def increment(metric, request=None, ignore_staff=True, ignore_anonymous=False):
    if request and ignore_staff and request.user.is_authenticated and request.user.is_staff:
        return

    if request and ignore_anonymous and not request.user.is_authenticated:
        return

    statsd.incr(f"platform.{metric}")
    if DATADOG_METRICS:
        datadog_statsd.increment(f"platform.{metric}", tags=DATADOG_TAGS)


def request_start(request):
    metric_id = f"platform.request.{re.sub('[^a-zA-Z]+', '', request.path)}.{request.method}"
    timer = statsd.timer(metric_id, rate=1)
    timer.start()

    return {
        'Request-Timer': timer,
        'Request-Metric-ID': metric_id,
        'Request-Metric-Start': int(round(timer._start_time * 1000))
    }


def request_stop(metrics, response):
    metrics['Request-Timer'].stop()
    metrics['Request-Metric-Millis'] = metrics['Request-Timer'].ms

    statsd.incr(metrics['Request-Metric-ID'])
    statsd.incr(f"{metrics['Request-Metric-ID']}.{response.status_code}")

    if DATADOG_METRICS:
        datadog_statsd.increment(metrics['Request-Metric-ID'], tags=DATADOG_TAGS)
        datadog_statsd.increment(f"{metrics['Request-Metric-ID']}.{response.status_code}", tags=DATADOG_TAGS)

        datadog_statsd.timing(metrics['Request-Metric-ID'] + ".time", metrics['Request-Timer'].ms, tags=DATADOG_TAGS)

    metrics.pop('Request-Timer')

    for name, value in metrics.items():
        response.headers[name] = (name, str(value))


def task_start(task_name):
    metric_id = f"platform.task.{task_name}"
    timer = statsd.timer(metric_id, rate=1)
    timer.start()

    return {
        'Task-Timer': timer,
        'Task-Metric-ID': metric_id,
        'Task-Metric-Start': int(round(timer._start_time * 1000))
    }


def task_stop(metrics):
    metrics['Task-Timer'].stop()
    metrics['Task-Metric-Millis'] = metrics['Task-Timer'].ms

    statsd.incr(metrics['Task-Metric-ID'])

    if DATADOG_METRICS:
        datadog_statsd.increment(metrics['Task-Metric-ID'], tags=DATADOG_TAGS)

        datadog_statsd.timing(metrics['Task-Metric-ID'] + ".time", metrics['Task-Timer'].ms, tags=DATADOG_TAGS)

    metrics.pop('Task-Timer')
