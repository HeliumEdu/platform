import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.8'

logger = logging.getLogger(__name__)


@login_required
def settings(request):
    metricutils.increment('view.settings', request)

    return render(request, "settings/main.html")
