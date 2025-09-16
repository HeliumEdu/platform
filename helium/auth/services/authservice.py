__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.27"

import logging

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response

from helium.auth.tasks import send_password_reset_email, send_registration_email
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


def forgot_password(request):
    """
    Generate a new password and send an email to the email specified in the request. For security purposes, whether
    the email exists in the system or not, the same response "success" will be shown the user.

    :param request: the request being processed
    :return: a 200 Response upon success
    """
    if 'email' not in request.data:
        raise ValidationError("'email' is required")

    try:
        user = get_user_model().objects.get(email=request.data['email'])

        # Generate a random password for the user
        password = get_user_model().objects.make_random_password()
        user.set_password(password)
        user.save()

        logger.info(f'Reset password for user with email {user.email}')

        metricutils.increment('action.user.password-reset', request)

        send_password_reset_email.delay(user.email, password)

        request.session.modified = True
    except get_user_model().DoesNotExist:
        logger.info(f'A visitor tried to reset the password for an unknown email address of {request.data["email"]}')

    return Response(status=status.HTTP_204_NO_CONTENT)


def verify_email(request):
    """
    Process the code for the given user, verifying their email address and marking them as active (if not already).

    :param request: the request being processed
    :return: a 200 Response upon success
    """
    if 'username' not in request.GET or 'code' not in request.GET:
        raise ValidationError("'username' and 'password' must be given as query parameters")

    try:
        user = get_user_model().objects.get(username=request.GET['username'], verification_code=request.GET['code'])

        if not user.is_active:
            user.is_active = True
            user.save()

            metricutils.increment('action.user.verified', request)

            logger.info(f'Completed registration and verification for user {user.username}')

            if request.GET.get('welcome-email', 'true') == 'true':
                send_registration_email.delay(user.email)
            else:
                logger.info('Welcome email not sent, flag disabled')
        elif user.email_changing:
            user.email = user.email_changing
            user.email_changing = None
            user.save()

            metricutils.increment('action.user.email-changed', request)

            logger.info(f'Verified new email for user {user.username}')

        return Response(status=status.HTTP_204_NO_CONTENT)
    except get_user_model().DoesNotExist:
        raise NotFound('No User matches the given query.')
