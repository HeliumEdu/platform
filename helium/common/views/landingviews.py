"""
Unauthenticated landing views.
"""

import logging

from django.shortcuts import render, redirect
from statsd.defaults.django import statsd

from helium.users.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def home(request):
    if authservice.is_anonymous_or_non_staff(request.user):
        statsd.incr('platform.view.home')

    return render(request, "home.html")


def support(request):
    statsd.incr('platform.view.support')

    return redirect('https://heliumedu.uservoice.com')


def terms(request):
    statsd.incr('platform.view.terms')

    return render(request, "terms.html")


def privacy(request):
    statsd.incr('platform.view.privacy')

    return render(request, "privacy.html")


def press(request):
    statsd.incr('platform.view.press')

    return render(request, "press.html")


def about(request):
    statsd.incr('platform.view.about')

    return render(request, "about.html")


def contact(request):
    statsd.incr('platform.view.contact')

    return render(request, "contact.html")
