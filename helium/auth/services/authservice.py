__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.contrib.auth import get_user_model
from django.core.cache import cache
from firebase_admin import auth as firebase_auth
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, Throttled, AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.models import UserOAuthProvider
from helium.auth.serializers.userserializer import UserSerializer
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

        # Only reset password for users with usable passwords (not OAuth-only users)
        if user.has_usable_password():
            # Generate a random password for the user
            password = get_user_model().objects.make_random_password()
            user.set_password(password)
            user.save()

            logger.info(f'Reset password for user with email {user.email}')

            send_password_reset_email.delay(user.email, password)

            metricutils.increment('action.user.password-reset', request=request, user=user)
        else:
            # OAuth-only user - don't create a password for security reasons
            logger.info(f'Password reset requested for OAuth-only user {user.email}, ignoring for security')
            metricutils.increment('action.user.password-reset.oauth-blocked', request=request, user=user)
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


def oauth_login(request, provider_name):
    """
    Authenticate or create a user via OAuth Sign-In using a Firebase ID token.

    :param request: the request being processed (must contain 'id_token' in data)
    :param provider_name: the OAuth provider name (e.g., 'Google', 'Apple')
    :return: a 200 Response with access and refresh tokens
    """
    if 'id_token' not in request.data:
        raise ValidationError("'id_token' is required")

    id_token = request.data['id_token']

    try:
        # Verify the Firebase ID token
        decoded_token = firebase_auth.verify_id_token(id_token)
        email = decoded_token.get('email')
        email_verified = decoded_token.get('email_verified', False)

        if not email:
            raise AuthenticationFailed(f"Email not provided by {provider_name} account")

        if not email_verified:
            raise AuthenticationFailed(f"Email not verified by {provider_name}")

        # Try to find existing user by email
        try:
            user = get_user_model().objects.get(email=email)
            logger.info(f'Existing user {user.id} logged in via {provider_name} Sign-In')
            metricutils.increment(f'action.user.{provider_name.lower()}-login', request=request, user=user)
        except get_user_model().DoesNotExist:
            # Generate unique username from email
            base_username = email.split('@')[0]
            username = base_username
            counter = 1

            while get_user_model().objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            serializer = UserSerializer()
            user = serializer.create_from_oauth({
                'username': username,
                'email': email,
            })

            logger.info(f'New user {user.id} created via {provider_name} Sign-In with username {username}')

            metricutils.increment(f'action.user.{provider_name.lower()}-signup', request=request, user=user)

        # Link or update OAuth provider for this user
        provider_uid = decoded_token.get('uid')
        provider_key = provider_name.lower()

        oauth_provider, created = UserOAuthProvider.objects.update_or_create(
            user=user,
            provider=provider_key,
            defaults={
                'provider_user_id': provider_uid,
            }
        )

        if created:
            logger.info(f'Linked {provider_name} OAuth provider to user {user.id}')
        else:
            logger.info(f'Updated {provider_name} OAuth provider last_used_at for user {user.id}')

        token = RefreshToken.for_user(user)

        return Response({
            'access': str(token.access_token),
            'refresh': str(token),
        }, status=status.HTTP_200_OK)

    except firebase_auth.ExpiredIdTokenError:
        logger.warning('Expired Firebase ID token')
        raise AuthenticationFailed(f'{provider_name} Sign-In token has expired')
    except firebase_auth.InvalidIdTokenError as e:
        logger.warning(f'Invalid Firebase ID token: {str(e)}')
        raise AuthenticationFailed(f'Invalid {provider_name} Sign-In token')
    except (ValidationError, AuthenticationFailed):
        # Re-raise validation and authentication errors
        raise
    except Exception as e:
        logger.error(f'{provider_name} Sign-In error: {str(e)}', exc_info=True)
        raise AuthenticationFailed(f'{provider_name} Sign-In authentication failed')


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
