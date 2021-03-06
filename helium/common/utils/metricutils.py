import os
import re

from django.conf import settings
from statsd.defaults.django import statsd

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
    DATADOG_TAGS = [f"env:{os.environ.get('ENVIRONMENT')}"]

__author__ = "Alex Laird"
__copyright__ = "Copyright 2021, Helium Edu"
__version__ = "1.4.46"


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

        datadog_statsd.timing(metrics['Request-Metric-ID'], metrics['Request-Timer'].ms, tags=DATADOG_TAGS)

    metrics.pop('Request-Timer')

    for name, value in metrics.items():
        response._headers[name] = (name, str(value))
