"""
Authenticated views for displaying user details.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from statsd.defaults.django import statsd

from helium.users.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@login_required
def settings(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.account.settings')

    return render(request, "account/settings.html")
