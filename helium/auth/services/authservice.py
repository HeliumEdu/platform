import logging

from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.response import Response

from helium.auth.tasks import send_password_reset_email, send_registration_email
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.0'

logger = logging.getLogger(__name__)


def forgot_password(request):
    if 'email' not in request.data:
        raise ValidationError("'email' is required")

    try:
        user = get_user_model().objects.get(email=request.data['email'])

        # Generate a random password for the user
        password = get_user_model().objects.make_random_password()
        user.set_password(password)
        user.save()

        logger.info('Reset password for user with email {}'.format(user.email))

        send_password_reset_email.delay(user.email, password)

        request.session.modified = True
    except get_user_model().DoesNotExist:
        logger.info('A visitor tried to reset the password for an unknown email address of {}'.format(
            request.data['email']))

    return Response()


def verify_email(request):
    if 'username' not in request.GET or 'code' not in request.GET:
        raise ValidationError("'username' and 'password' must be given as query parameters")

    try:
        user = get_user_model().objects.get(username=request.GET['username'], verification_code=request.GET['code'])

        if not user.is_active:
            user.is_active = True
            user.save()

            metricutils.increment('action.user.verified', request)

            logger.info('Completed registration and verification for user {}'.format(user.username))

            send_registration_email.delay(user.email)
        elif user.email_changing:
            user.email = user.email_changing
            user.email_changing = None
            user.save()

            metricutils.increment('action.user.email-changed', request)

            logger.info('Verified new email for user {}'.format(user.username))

        return Response()
    except get_user_model().DoesNotExist:
        raise NotFound()
