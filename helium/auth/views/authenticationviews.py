"""
Unauthenticated views for user authentication.
"""
import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from statsd.defaults.django import statsd

from helium.common.utils.viewutils import set_request_status, get_request_status, set_response_status, clear_response_status
from helium.auth.forms.userloginform import UserLoginForm
from helium.auth.forms.userregisterform import UserRegisterForm
from helium.auth.services import authservice

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def register(request):
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('planner'))

    redirect = None

    if request.user.is_authenticated():
        redirect = reverse('planner')

    if request.method == 'POST':
        user_register_form = UserRegisterForm(request.POST)
        if user_register_form.is_valid():
            user_register_form.save()

            redirect = authservice.process_register(request, user_register_form.instance)
        else:
            set_request_status(request, 'warning', user_register_form.errors.values()[0][0])
    else:
        user_register_form = UserRegisterForm()

    # Check if a status has been set (either by this view or another view from which we were redirect)
    status = get_request_status(request, '')

    if redirect:
        response = HttpResponseRedirect(redirect)

        # In the case of a redirect, we move the status to the response so it gets passed
        set_response_status(response, status)

        return response
    else:
        if authservice.is_anonymous_or_non_staff(request.user):
            statsd.incr('platform.view.register')

        data = {
            'user_register_form': user_register_form,
            'status': status
        }

        return render(request, 'authentication/register.html', {'data': data})


def verify(request):
    if request.user.is_authenticated():
        authservice.process_logout(request)

    if request.method == 'GET' and 'username' in request.GET and 'code' in request.GET:
        redirect = authservice.process_verification(request, request.GET['username'], request.GET['code'])
    else:
        redirect = reverse('register')

    return HttpResponseRedirect(redirect)


def login(request):
    redirect = None
    status = None

    user_login_form = UserLoginForm()
    if request.user.is_authenticated():
        redirect = HttpResponseRedirect(reverse('planner'))
    else:
        if request.method == 'POST':
            user_login_form = UserLoginForm(request.POST)
            if user_login_form.is_valid():
                username = user_login_form.cleaned_data.get('username')
                password = user_login_form.cleaned_data.get('password')

                redirect = authservice.process_login(request, username, password)

                if authservice.is_anonymous_or_non_staff(request.user):
                    statsd.incr('platform.action.user-logged-in')
            else:
                set_request_status(request, 'warning', user_login_form.errors.values()[0][0])

        status = get_request_status(request, None)

    # Login was successful, or the user is already logged in
    if redirect:
        redirect = HttpResponseRedirect(redirect)

        return redirect
    else:
        http_status = 200
        if request.method == 'POST':
            http_status = 401

        data = {
            'user_login_form': user_login_form,
            'status': status
        }

        response = render(request, 'authentication/login.html', {'data': data}, status=http_status)
        clear_response_status(response)
        return response


def logout(request):
    if request.user.is_authenticated():
        authservice.process_logout(request)

    return HttpResponseRedirect(reverse('planner'))


def forgot(request):
    redirect = None
    status = None

    if request.user.is_authenticated():
        redirect = reverse('settings')
    else:
        if request.method == 'POST':
            redirect = authservice.process_forgot_password(request)

        status = get_request_status(request)

    if not redirect:
        if authservice.is_anonymous_or_non_staff(request.user):
            statsd.incr('platform.view.forgotpassword')

        data = {
            'status': status
        }

        return render(request, 'authentication/forgot.html', {'data': data})
    else:
        response = HttpResponseRedirect(redirect)

        set_response_status(response, status)

        return response
