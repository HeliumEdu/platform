import six
from statsd.defaults.django import statsd

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'


def increment(metric, request=None, ignore_staff=True, ignore_anonymous=False):
    if request and ignore_staff and request.user.is_authenticated() and request.user.is_staff:
        return

    if request and ignore_anonymous and not request.user.is_authenticated():
        return

    statsd.incr("platform.{}".format(metric))


def request_start(request):
    metric_id = "platform.{}.{}".format(request.path.replace('/', ''), request.method)
    timer = statsd.timer(metric_id + '.timer', rate=1)
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

    metrics.pop('Request-Timer')

    for name, value in metrics.items():
        response._headers[name] = (name, str(value))
