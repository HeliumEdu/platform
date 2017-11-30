"""
Authenticated views for displaying planner pages.
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
def calendar(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.calendar')

    return render(request, "calendar.html")


@login_required
def classes(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.classes')

    return render(request, "classes.html")


@login_required
def materials(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.materials')

    return render(request, "materials.html")


@login_required
def grades(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.grades')

    return render(request, "grades.html")
