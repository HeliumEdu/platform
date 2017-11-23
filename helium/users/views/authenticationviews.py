"""
Authentication view entrance functions.
"""
import ast
import logging

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from statsd.defaults.django import statsd

from helium.users import tasks
from helium.users.forms.usercreationform import UserCreationForm
from helium.users.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


def register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('planner'))

    redirect = None

    if request.user.is_authenticated():
        redirect = reverse('planner')

    if request.method == 'POST':
        user_form = UserCreationForm(request.POST)
        if user_form.is_valid():
            user_form.save()

            redirect = authservice.process_register(request, user_form.instance)

            if not user_form.instance.email.endswith('@heliumedu.com'):
                statsd.incr('platform.vol.user-added')
        else:
            request.session['status'] = {'type': 'warning', 'msg': 'Correct the errors below and try again.'}
    else:
        user_form = UserCreationForm()

    status = request.session.get('status', '')
    if 'status' in request.session:
        del request.session['status']

    if redirect:
        return HttpResponseRedirect(redirect)
    else:
        if authservice.is_anonymous_or_non_admin(request.user):
            statsd.incr('platform.view.register')

        data = {
            'user_form': user_form,
            'status': status
        }

        return render(request, 'authentication/register.html', {'data': data})


def login(request):
    redirect = None
    status = None

    if request.user.is_authenticated():
        redirect = reverse('planner')
    else:
        if request.method == 'POST':
            redirect = authservice.process_login(request)

            if authservice.is_anonymous_or_non_admin(request.user):
                statsd.incr('platform.action.user-logged-in')

        status = request.session.get('status', None)
        if not status:
            status = request.COOKIES.get('status', None)
            if status:
                status = ast.literal_eval(status)
        if 'status' in request.session:
            del request.session['status']

    if redirect:
        redirect = HttpResponseRedirect(redirect)

        return redirect
    else:
        response_status = 200
        if request.method == 'POST':
            response_status = 401

        data = {
            'status': status
        }

        response = render(request, 'authentication/login.html', {'data': data}, status=response_status)
        if 'status' in request.COOKIES:
            response.delete_cookie(key='status')
        return response


def logout(request):
    if request.user.is_authenticated():
        authservice.process_logout(request)

    return HttpResponseRedirect(reverse('planner'))


def forgot(request):
    redirect = None
    status = None

    if request.user.is_authenticated():
        redirect = reverse('password')
    else:
        if request.method == 'POST':
            redirect = authservice.process_forgot_password(request)

        status = request.session.get('status', None)
        if 'status' in request.session:
            del request.session['status']

    if not redirect:
        if authservice.is_anonymous_or_non_admin(request.user):
            statsd.incr('platform.view.forgotpassword')

        data = {
            'status': status
        }

        return render(request, 'authentication/password.html', {'data': data})
    else:
        response = HttpResponseRedirect(redirect)
        if status:
            response.set_cookie('status', status)
        return response
