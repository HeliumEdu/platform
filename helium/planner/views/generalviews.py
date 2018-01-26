import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@login_required
def calendar(request):
    metricutils.increment('view.calendar', request)

    return render(request, "calendar/main.html")


@login_required
def classes(request):
    metricutils.increment('view.classes', request)

    return render(request, "classes/main.html")


@login_required
def materials(request):
    metricutils.increment('view.materials', request)

    return render(request, "materials/main.html")


@login_required
def grades(request):
    metricutils.increment('view.grades', request)

    return render(request, "grades/main.html")
