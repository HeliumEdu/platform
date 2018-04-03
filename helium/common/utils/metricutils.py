import re

from django.conf import settings
from statsd.defaults.django import statsd

DATADOG_METRICS = False
if settings.DATADOG_API_KEY:
    from datadog import initialize

    options = {
        'api_key': settings.DATADOG_API_KEY,
        'app_key': settings.DATADOG_APP_KEY
    }

    initialize(**options)

    from datadog import statsd as datadog_statsd

    DATADOG_METRICS = True

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.3'


def increment(metric, request=None, ignore_staff=True, ignore_anonymous=False):
    if request and ignore_staff and request.user.is_authenticated and request.user.is_staff:
        return

    if request and ignore_anonymous and not request.user.is_authenticated:
        return

    statsd.incr("platform.{}".format(metric))
    if DATADOG_METRICS:
        datadog_statsd.increment("platform.{}".format(metric))


def request_start(request):
    metric_id = "platform.request.{}.{}".format(re.sub("[^a-zA-Z]+", "", request.path), request.method)
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
    statsd.incr("{}.{}".format(metrics['Request-Metric-ID'], response.status_code))

    if DATADOG_METRICS:
        datadog_statsd.increment(metrics['Request-Metric-ID'])
        datadog_statsd.increment("{}.{}".format(metrics['Request-Metric-ID'], response.status_code))

        datadog_statsd.timing(metrics['Request-Metric-ID'], metrics['Request-Timer'].ms)

    metrics.pop('Request-Timer')

    for name, value in metrics.items():
        response._headers[name] = (name, str(value))
