__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.49"

import logging
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from conf.celery import app
from helium.common.utils import commonutils, metricutils

logger = logging.getLogger(__name__)


@app.task
def send_verification_email(email, username, verification_code):
    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Verification code: {verification_code}')
        return

    commonutils.send_multipart_email('email/verification',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'username': username,
                                         'verification_code': verification_code,
                                         'verify_url': f"{settings.PROJECT_APP_HOST}/verify",
                                     },
                                     'Verify Your Email Address with Helium', [email])

    logger.debug(f"Verification email with code \"{verification_code}\" sent to {username}")

    metricutils.increment('task.email.verification.sent')


@app.task
def send_registration_email(email):
    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Welcome email not sent.')
        return

    commonutils.send_multipart_email('email/register',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'login_url': f"{settings.PROJECT_APP_HOST}/login",
                                     },
                                     'Welcome to Helium', [email], [settings.DEFAULT_FROM_EMAIL])

    logger.debug(f"Registration email sent to {email}")

    metricutils.increment('task.email.registration.sent')


@app.task
def send_password_reset_email(email, temp_password):
    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Reset password: {temp_password}')
        return

    commonutils.send_multipart_email('email/forgot',
                                     {
                                         'password': temp_password,
                                         'settings_url': f"{settings.PROJECT_APP_HOST}/settings",
                                         'support_url': f"{settings.PROJECT_APP_HOST}/support",
                                     },
                                     'Your Helium Password Has Been Reset', [email])

    logger.debug(f"Password reset email sent to {email}")

    metricutils.increment('task.email.password-reset.sent')


@app.task
def delete_user(user_id):
    metrics = metricutils.task_start("delete_user")

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        user = get_user_model().objects.get(pk=user_id)

        outstanding_tokens = list(OutstandingToken.objects.filter(user=user))
        blacklisted_tokens = list(BlacklistedToken.objects.filter(token__user=user))

        user.delete()

        for token in outstanding_tokens + blacklisted_tokens:
            token.delete()

        metricutils.increment('task.user.deleted', user=user)
    except get_user_model().DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        return

    metricutils.task_stop(metrics)


@app.task
def blacklist_refresh_token(token):
    try:
        RefreshToken(token).blacklist()

        metricutils.increment('task.token.refresh.blacklisted')
    except TokenError:
        logger.info('Skipping, token is already blacklisted.')


@app.task
def purge_refresh_tokens():
    metrics = metricutils.task_start("purge_refresh_tokens")

    deleted, num_deleted = OutstandingToken.objects.filter(
        expires_at__lte=datetime.now().replace(tzinfo=pytz.utc)).delete()

    metricutils.increment('task.token.refresh.purged', value=num_deleted)

    metricutils.task_stop(metrics)


@app.task
def purge_unverified_users():
    metrics = metricutils.task_start("purge_unverified_users")

    for user in get_user_model().objects.filter(
            is_active=False,
            created_at__lte=datetime.now().replace(tzinfo=pytz.utc) - timedelta(
                days=settings.UNVERIFIED_USER_TTL_DAYS)):
        logger.info(
            f'Deleting user {user.username}, never verified or activated after {settings.UNVERIFIED_USER_TTL_DAYS} days.')

        user.delete()

        metricutils.increment('task.purge.unverified-user')

    metricutils.task_stop(metrics)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to check for expired refresh tokens periodically
    sender.add_periodic_task(settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC, purge_refresh_tokens.s())
    # Add schedule to purge unverified users that don't finish setting up their account
    sender.add_periodic_task(settings.PURGE_UNVERIFIED_USERS_FREQUENCY_SEC, purge_unverified_users.s())
