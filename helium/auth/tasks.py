import logging
from datetime import datetime, timedelta

import pytz
from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import commonutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.22'

logger = logging.getLogger(__name__)


@app.task
def send_verification_email(email, username, verification_code):
    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Verification code: {}'.format(verification_code))
        return

    commonutils.send_multipart_email('email/verification',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'username': username,
                                         'verification_code': verification_code,
                                         'verify_url': "{}/verify".format(settings.PROJECT_APP_HOST),
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
                                         'login_url': "{}/login".format(settings.PROJECT_APP_HOST),
                                     },
                                     'Welcome to Helium', [email], [settings.DEFAULT_FROM_EMAIL])


@app.task
def send_password_reset_email(email, temp_password):
    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Reset password: {}'.format(temp_password))
        return

    commonutils.send_multipart_email('email/forgot',
                                     {
                                         'password': temp_password,
                                         'settings': "{}/settings".format(settings.PROJECT_APP_HOST),
                                         'support': "{}/support".format(settings.PROJECT_APP_HOST),
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
        logger.info('User {} does not exist. Nothing to do.'.format(user_id))

        return


@app.task
def expire_auth_tokens():
    from rest_framework.authtoken.models import Token

    Token.objects.filter(
        created__lte=datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=settings.AUTH_TOKEN_TTL_DAYS)).delete()


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to check for expired auth tokens periodically
    sender.add_periodic_task(crontab(hour=settings.AUTH_TOKEN_EXPIRE_FREQUENCY_HOUR, minute=0), expire_auth_tokens.s())
