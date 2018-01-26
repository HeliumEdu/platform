from statsd.defaults.django import statsd

from helium.auth.utils import userutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'


def increment(metric, request=None, ignore_staff=True, ignore_anonymous=False):
    if request and ignore_staff and not userutils.is_anonymous(request.user) and userutils.is_staff(request.user):
        return

    if request and ignore_anonymous and userutils.is_anonymous(request.user):
        return

    statsd.incr("platform.{}".format(metric))
