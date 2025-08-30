__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.8"

import logging
from datetime import datetime, timedelta

import pytz
from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import commonutils

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


@app.task
def delete_user(user_id):
    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    try:
        user = get_user_model().objects.get(pk=user_id)

        user.delete()
    except get_user_model().DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        return


@app.task
def expire_auth_tokens():
    from rest_framework.authtoken.models import Token

    Token.objects.filter(
        created__lte=datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.AUTH_TOKEN_TTL_DAYS)).delete()


@app.task
def purge_unverified_users():
    for user in get_user_model().objects.filter(
            is_active=False,
            created_at__lte=datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS)):
        logger.info(
            f'Deleting user {user.username}, never verified or activated after {settings.UNVERIFIED_USER_TTL_DAYS} days.')

        user.delete()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to check for expired auth tokens periodically
    sender.add_periodic_task(crontab(hour=settings.AUTH_TOKEN_EXPIRY_HOUR, minute=0), expire_auth_tokens.s())
    # Add schedule to purge unverified users that don't finish setting up their account
    sender.add_periodic_task(settings.PURGE_UNVERIFIED_USERS_FREQUENCY_SEC, purge_unverified_users.s())
