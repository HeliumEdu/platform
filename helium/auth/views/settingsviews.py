"""
Views for interacting with user details.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render

from helium.auth.services import subscriptionservice
from helium.common.utils import metricutils
from helium.common.utils.viewutils import set_request_status, get_request_status

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def unsubscribe(request):
    unsubsribed = False
    if request.method == 'GET' and 'username' in request.GET and 'code' in request.GET:
        unsubsribed = subscriptionservice.process_unsubscribe(request.GET['username'], request.GET['code'])

    if unsubsribed:
        set_request_status(request, 'warning',
                           'Sorry we bothered you! You won\'t receive emails from The Helium Team in the future.')

        data = {
            'status': get_request_status(request)
        }

        return render(request, 'settings/unsubscribe.html', data)
    else:
        return HttpResponseRedirect('home')


@login_required
def settings(request):
    metricutils.increment(request, 'view.settings')

    return render(request, "settings/main.html")
