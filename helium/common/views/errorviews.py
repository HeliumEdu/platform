"""
Unauthenticated error views.
"""

import logging

from django.shortcuts import render_to_response
from django.template import RequestContext

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def bad_request(request):
    return render_to_response("errors/400.html",
                              context=RequestContext(request),
                              status=400)


def unauthorized(request):
    return render_to_response("errors/401.html",
                              context=RequestContext(request),
                              status=401)


def forbidden(request):
    return render_to_response("errors/403.html",
                              context=RequestContext(request),
                              status=403)


def not_found(request):
    return render_to_response("errors/404.html",
                              context=RequestContext(request),
                              status=404)


def internal_server_error(request):
    return render_to_response("errors/500.html",
                              context=RequestContext(request),
                              status=500)


def website_unavailable(request):
    return render_to_response("errors/503.html",
                              context=RequestContext(request),
                              status=503)
