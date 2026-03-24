__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from firebase_admin import auth as firebase_auth
from rest_framework import status
from rest_framework.exceptions import ValidationError, NotFound, Throttled, AuthenticationFailed
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from helium.auth.models import UserOAuthProvider
from helium.auth.serializers.userserializer import UserSerializer
from helium.auth.tasks import send_password_reset_email, send_registration_email, send_verification_email
from helium.auth.utils.userutils import generate_verification_code, generate_unique_username_from_email
from helium.common.utils import metricutils
from helium.feed.models import ExternalCalendar
from helium.importexport.tasks import import_example_schedule
from helium.planner.models import CourseGroup, Event, MaterialGroup, Note

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

            logger.info(f'Reset password for user {user.pk}')

            send_password_reset_email.apply_async(
                args=(user.email, password),
                priority=settings.CELERY_PRIORITY_HIGH,
            )

            metricutils.increment('action.user.password-reset', request=request, user=user)
        else:
            # OAuth-only user - don't create a password for security reasons
            logger.info(f'Password reset requested for OAuth-only user {user.pk}, ignoring for security')
            metricutils.increment('action.user.password-reset.oauth-blocked', request=request, user=user)
    except get_user_model().DoesNotExist:
        logger.info(f'Password reset requested for unknown account identifier')

    return Response(status=status.HTTP_202_ACCEPTED)


def verify_email(request):
    """
    Process the code for the given user, verifying their email address and marking them as active (if not already).

    :param request: the request being processed
    :return: a 202 Response upon success, with user data and auth tokens
    """
    if 'username' not in request.GET or 'code' not in request.GET:
        raise ValidationError("'username' and 'code' must be given as query parameters")

    identifier = request.GET['username']
    code = request.GET['code']

    try:
        user = get_user_model().objects.get(
            (Q(username__iexact=identifier) | Q(email__iexact=identifier) | Q(email_changing__iexact=identifier)),
            verification_code=code,
        )

        if not user.is_active:
            user.is_active = True
            user.save()

            logger.info(f'Completed registration and verification for user {user.pk}')

            if request.GET.get('welcome-email', 'true') == 'true':
                send_registration_email.apply_async(
                    args=(user.email,),
                    priority=settings.CELERY_PRIORITY_HIGH,
                )
            else:
                logger.info('Welcome email not sent, flag disabled')

            metricutils.increment('action.user.verified', request=request, user=user)
        elif user.email_changing:
            user.email = user.email_changing
            user.email_changing = None
            user.save()

            logger.info(f'Verified new email for user {user.pk}')

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
    Resend the verification email for an inactive user account or an active user changing their email.
    Rate limited to once per 60 seconds per user.

    :param request: the request being processed
    :return: a 202 Response upon success, 429 if rate limited
    """
    if 'username' not in request.GET:
        raise ValidationError("'username' must be given as a query parameter")

    identifier = request.GET['username']
    cache_key = f'resend_verification:{identifier.strip().lower()}'

    # Check rate limit
    if cache.get(cache_key):
        raise Throttled(detail='Please wait before requesting another verification email.')

    try:
        user = get_user_model().objects.get(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        )

        # Determine if this is a new registration or email change verification
        if user.is_active and not user.email_changing:
            # Active user with no pending email change - nothing to resend
            logger.info(f'Resend verification requested for already active user {user.pk} with no pending email change')
            return Response(status=status.HTTP_202_ACCEPTED)

        # Generate new verification code and send email
        user.verification_code = generate_verification_code()
        user.save()

        # Send to email_changing if set (active user changing email), otherwise to email (new registration)
        target_email = user.email_changing if user.email_changing else user.email

        send_verification_email.apply_async(
            args=(target_email, user.username, user.verification_code),
            priority=settings.CELERY_PRIORITY_HIGH,
        )

        logger.info(f'Resent verification email for user {user.pk} to {target_email}')

        metricutils.increment('action.user.verification-resent', request=request, user=user)

        # Set rate limit
        cache.set(cache_key, True, RESEND_VERIFICATION_COOLDOWN_SECONDS)

        return Response(status=status.HTTP_202_ACCEPTED)
    except get_user_model().DoesNotExist:
        # Don't reveal whether user exists - return success anyway
        logger.info(f'Resend verification requested for unknown account identifier')
        return Response(status=status.HTTP_202_ACCEPTED)


SUPPORTED_OAUTH_PROVIDERS = ['google', 'apple']


def oauth_login(request):
    """
    Authenticate or create a user via OAuth Sign-In using a Firebase ID token.

    :param request: the request being processed (must contain 'id_token' and 'provider' in data)
    :return: a 200 Response with access and refresh tokens
    """
    if 'id_token' not in request.data:
        raise ValidationError("'id_token' is required")

    if 'provider' not in request.data:
        raise ValidationError("'provider' is required")

    provider = request.data['provider'].lower()
    if provider not in SUPPORTED_OAUTH_PROVIDERS:
        raise ValidationError(f"'provider' must be one of: {', '.join(SUPPORTED_OAUTH_PROVIDERS)}")

    provider_name = provider.capitalize()

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

        provider_uid = decoded_token.get('uid')
        provider_key = provider_name.lower()

        # Check if this OAuth provider UID is already linked to a user
        existing_oauth = UserOAuthProvider.objects.select_related('user').filter(
            provider=provider_key,
            provider_user_id=provider_uid,
        ).first()

        # Try to find existing user by email
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            user = None

        # Security check: if UID is linked to a different user than the email lookup found,
        # fail loudly rather than guess which account to use
        if existing_oauth and user and existing_oauth.user_id != user.id:
            logger.error(
                f'{provider_name} Sign-In conflict: provider UID {provider_uid} is linked to user '
                f'{existing_oauth.user_id}, but email {email} belongs to user {user.id}. '
                f'Manual investigation required.'
            )
            raise AuthenticationFailed(
                f'{provider_name} Sign-In failed due to an account conflict. '
                f'Please contact support for assistance.'
            )

        is_new_user = False
        if existing_oauth:
            # UID already linked - use that user
            user = existing_oauth.user

            # Update last_used_at timestamp (auto_now field)
            existing_oauth.save(update_fields=['last_used_at'])

            # Activate inactive users since OAuth provides verified email
            if not user.is_active:
                user.is_active = True
                user.save()
                logger.info(f'Activated inactive user {user.id} via {provider_name} Sign-In')
                metricutils.increment(f'action.user.{provider_name.lower()}-activated', request=request, user=user)

            logger.info(f'Existing user {user.id} logged in via {provider_name} Sign-In (matched by provider UID)')
            metricutils.increment(f'action.user.{provider_name.lower()}-login', request=request, user=user)

        elif user:
            # No OAuth link by UID, but found user by email - link/update and login
            # Activate inactive users since OAuth provides verified email
            if not user.is_active:
                user.is_active = True
                user.save()
                logger.info(f'Activated inactive user {user.id} via {provider_name} Sign-In')
                metricutils.increment(f'action.user.{provider_name.lower()}-activated', request=request, user=user)

            logger.info(f'Existing user {user.id} logged in via {provider_name} Sign-In')
            metricutils.increment(f'action.user.{provider_name.lower()}-login', request=request, user=user)

            # Link or update OAuth provider for this existing user
            # Uses (user, provider) as the lookup key since the provider_user_id may have
            # changed if the Firebase user was deleted and recreated
            _, created = UserOAuthProvider.objects.update_or_create(
                user=user,
                provider=provider_key,
                defaults={'provider_user_id': provider_uid},
            )
            if created:
                logger.info(f'Linked {provider_name} OAuth provider to user {user.id}')
            else:
                logger.info(f'Updated {provider_name} OAuth provider UID for user {user.id}')

        else:
            # No OAuth link and no user with this email - create new user
            is_new_user = True
            username = generate_unique_username_from_email(email)

            serializer = UserSerializer()
            user = serializer.create_from_oauth({
                'username': username,
                'email': email,
            })

            # Import the example schedule for the user
            import_example_schedule.apply_async(
                args=(user.pk,),
                priority=settings.CELERY_PRIORITY_HIGH,
            )

            logger.info(f'New user {user.id} created via {provider_name} Sign-In')

            metricutils.increment(f'action.user.{provider_name.lower()}-signup', request=request, user=user)

            # Link OAuth provider to the new user
            UserOAuthProvider.objects.create(
                user=user,
                provider=provider_key,
                provider_user_id=provider_uid,
            )
            logger.info(f'Linked {provider_name} OAuth provider to new user {user.id}')

        update_last_login(None, user)
        if not is_new_user:
            user.last_activity = timezone.now()
            user.deletion_warning_count = 0
            user.deletion_warning_sent_at = None
            user.save(update_fields=['last_activity', 'deletion_warning_count', 'deletion_warning_sent_at'])

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
    # Only delete standalone notes (no linked entities) - linked notes are already
    # cascade-deleted when their parent entities are deleted above
    (Note.objects
     .for_user(user_id)
     .filter(example_schedule=True, homework__isnull=True, events__isnull=True, resources__isnull=True)
     .delete())

    metricutils.task_stop(metrics, user=user)
