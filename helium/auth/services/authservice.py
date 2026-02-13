__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, Throttled
from rest_framework.response import Response

from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.tasks import send_password_reset_email, send_registration_email, send_verification_email
from helium.auth.utils.userutils import generate_verification_code
from helium.common.utils import metricutils
from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, MaterialGroup, Event

logger = logging.getLogger(__name__)


def forgot_password(request):
    """
    Generate a new password and send an email to the address specified in the request. For security purposes, whether
    the email exists in the system or not, the same response "success" will be shown the user.

    :param request: the request being processed
    :return: a 202 Response upon success
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

        send_password_reset_email.delay(user.email, password)

        metricutils.increment('action.user.password-reset', request=request, user=user)
    except get_user_model().DoesNotExist:
        logger.info(f'A user tried to reset their password, but the given email address is unknown')

    return Response(status=status.HTTP_202_ACCEPTED)


def verify_email(request):
    """
    Process the code for the given user, verifying their email address and marking them as active (if not already).

    :param request: the request being processed
    :return: a 202 Response upon success, with user data and auth tokens
    """
    if 'username' not in request.GET or 'code' not in request.GET:
        raise ValidationError("'username' and 'code' must be given as query parameters")

    try:
        user = get_user_model().objects.get(username=request.GET['username'], verification_code=request.GET['code'])

        if not user.is_active:
            user.is_active = True
            user.save()

            logger.info(f'Completed registration and verification for user {user.username}')

            if request.GET.get('welcome-email', 'true') == 'true':
                send_registration_email.delay(user.email)
            else:
                logger.info('Welcome email not sent, flag disabled')

            metricutils.increment('action.user.verified', request=request, user=user)
        elif user.email_changing:
            user.email = user.email_changing
            user.email_changing = None
            user.save()

            logger.info(f'Verified new email for user {user.username}')

            metricutils.increment('action.user.email-changed', request=request, user=user)

        # Generate auth tokens for the verified user
        token = RefreshToken.for_user(user)

        return Response({
            'access': str(token.access_token),
            'refresh': str(token),
        }, status=status.HTTP_202_ACCEPTED)
    except get_user_model().DoesNotExist:
        raise NotFound('No User matches the given query.')


RESEND_VERIFICATION_COOLDOWN_SECONDS = 60


def resend_verification_email(request):
    """
    Resend the verification email for an inactive user account.
    Rate limited to once per 60 seconds per user.

    :param request: the request being processed
    :return: a 202 Response upon success, 429 if rate limited
    """
    if 'username' not in request.GET:
        raise ValidationError("'username' must be given as a query parameter")

    username = request.GET['username']
    cache_key = f'resend_verification:{username}'

    # Check rate limit
    if cache.get(cache_key):
        raise Throttled(detail='Please wait before requesting another verification email.')

    try:
        user = get_user_model().objects.get(username=username)

        if user.is_active:
            # Don't reveal whether user exists or is already active
            logger.info(f'Resend verification requested for already active user {username}')
            return Response(status=status.HTTP_202_ACCEPTED)

        # Generate new verification code and send email
        user.verification_code = generate_verification_code()
        user.save()

        send_verification_email.delay(user.email, user.username, user.verification_code)

        logger.info(f'Resent verification email for user {username}')

        metricutils.increment('action.user.verification-resent', request=request, user=user)

        # Set rate limit
        cache.set(cache_key, True, RESEND_VERIFICATION_COOLDOWN_SECONDS)

        return Response(status=status.HTTP_202_ACCEPTED)
    except get_user_model().DoesNotExist:
        # Don't reveal whether user exists - return success anyway
        logger.info(f'Resend verification requested for unknown user {username}')
        return Response(status=status.HTTP_202_ACCEPTED)


def delete_example_schedule(user_id):
    metrics = metricutils.task_start("user.exampleschedule.delete")

    try:
        user = get_user_model().objects.get(pk=user_id)
    except get_user_model().DoesNotExist:
        user = None

    (ExternalCalendar.objects
     .for_user(user_id)
     .filter(example_schedule=True)
     .delete())
    (CourseGroup.objects
     .for_user(user_id)
     .filter(example_schedule=True)
     .delete())
    (MaterialGroup.objects
     .for_user(user_id)
     .filter(example_schedule=True)
     .delete())
    (Event.objects
     .for_user(user_id)
     .filter(example_schedule=True)
     .delete())

    metricutils.task_stop(metrics, user=user)
