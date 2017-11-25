"""
Unauthenticated view entrance functions.
"""

import logging

from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from statsd.defaults.django import statsd

from helium.users.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


def internal_server_error(request):
    return render_to_response("500.html",
                              context_instance=RequestContext(request),
                              status=500)


def bad_request(request):
    return render_to_response("400.html",
                              context_instance=RequestContext(request),
                              status=400)


def unauthorized(request):
    return render_to_response("401.html",
                              context_instance=RequestContext(request),
                              status=401)


def forbidden(request):
    return render_to_response("403.html",
                              context_instance=RequestContext(request),
                              status=403)


def home(request):
    if authservice.is_anonymous_or_non_admin(request.user):
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
