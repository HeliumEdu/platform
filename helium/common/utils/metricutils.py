from statsd.defaults.django import statsd

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'


def increment(metric, request=None, ignore_staff=True, ignore_anonymous=False):
    if request and ignore_staff and request.user.is_authenticated() and request.user.is_staff:
        return

    if request and ignore_anonymous and not request.user.is_authenticated():
        return

    statsd.incr("platform.{}".format(metric))
