"""
Unauthenticated view entrance functions.
"""

import logging

from django.shortcuts import render, render_to_response, redirect
from django.template import RequestContext
from statsd.defaults.django import statsd

from helium.common import tasks
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
    return redirect('https://heliumedu.zendesk.com/hc')


def contact(request):
    if request.method == 'POST':
        if 'name' in request.POST and 'email' in request.POST and 'subject' in request.POST and 'message' in request.POST:
            name = request.POST['name'].strip()
            email = request.POST['email']
            subject = request.POST['subject'].strip()
            body = request.POST['message'].strip()

            tasks.send_contact_email(name, email, subject, body)

            data = {
                'status': {'type': 'success',
                           'msg': 'Sent!'}
            }
        else:
            data = {
                'status': {'type': 'warning',
                           'msg': 'All form fields are required.'}
            }
    else:
        data = {}

    return render(request, "contact.html", {'data': data})
