"""
Authentication functions.
"""

import logging

from django.conf import settings
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.core.urlresolvers import reverse

from helium.users import tasks

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


def process_register(request, user):
    logger.info('Registered new user with username: ' + user.get_username())

    tasks.send_registration_email.delay(user.email, request.get_host())

    user = authenticate(username=request.POST['email'], password=request.POST['password1'])
    login(request, user)

    logger.info('Logged in user ' + user.get_username())
    redirect = reverse('planner')

    return redirect


def process_login(request):
    redirect = None
    if 'username' in request.POST and 'password' in request.POST:
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)
        error_msg = None
        if user is not None:
            if user.is_active:
                login(request, user)

                logger.info('Logged in user ' + username)

                redirect = reverse('planner')

                if request.POST.get('remember-me', False):
                    request.session.set_expiry(1209600)

                # If 'next' exists as a parameter in the URL, redirect to the specified page instead
                if 'next' in request.GET:
                    redirect = request.GET['next']
            else:
                logger.info('Inactive user ' + username + " attempted login")
                error_msg = 'Sorry, your account is not active. Check your email for a verification email if you recently registered, otherwise <a href="mailto:' + settings.EMAIL_ADDRESS + '">Contact support</a> and we\'ll help you sort this out!'
        else:
            logger.info('Non-existent user ' + username + " attempted login")
            error_msg = 'Oops! We don\'t recognize that account. Check to make sure you entered your credentials properly.'

        if error_msg is not None:
            request.session['status'] = {'type': 'warning', 'msg': error_msg}

    return redirect


def process_logout(request):
    email = request.user.email
    logout(request)
    logger.info('Logged out user ' + email)


def process_forgot_password(request):
    email = request.POST['email']
    redirect = None
    try:
        user = get_user_model().objects.get(email=email)

        # Generate a random password and save it to the user
        password = get_user_model().objects.make_random_password()
        user.set_password(password)
        user.save()
        logger.info('Reset password for user with email ' + email)

        tasks.send_password_reset.delay(user.email, password, request.get_host())

        request.session['status'] = {'type': 'info',
                                     'msg': 'You\'ve been emailed a temporary password. Login to your account immediately using the temporary password, then change your password.'}
        request.session.modified = True

        redirect = reverse('login')
    except get_user_model().DoesNotExist:
        logger.info('A visitor tried to reset the password for an unknown email address of ' + email)

        request.session['status'] = {'type': 'warning',
                                     'msg': 'Sorry, that email doesn\'t belong to any user in our system. <a href="mailto:' + settings.EMAIL_ADDRESS + '">Contact support</a> if you believe this is an error.'}

    return redirect


def is_password_valid(password):
    valid = True

    if len(password) < 8:
        valid = False

    first_isalpha = password[0].isalpha()
    if all(c.isalpha() == first_isalpha for c in password):
        valid = False

    return valid


def is_admin(user):
    return user.is_staff


def is_anonymous_or_non_admin(user):
    return not user.is_authenticated() or not is_admin(user)
