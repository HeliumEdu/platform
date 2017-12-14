"""
Common utility function.
"""

from statsd.defaults.django import statsd

from helium.auth.utils import userutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def increment(request, metric, ignore_staff=True, ignore_anonymous=False):
    if ignore_staff and not userutils.is_anonymous(request.user) and userutils.is_staff(request.user):
        return

    if ignore_anonymous and userutils.is_anonymous(request.user):
        return

    statsd.incr("platform.{}".format(metric))
