import logging

from django.conf import settings

from conf.celery import app
from helium.common.utils import commonutils, metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def send_verification_email(email, username, verification_code):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Verification code: {}'.format(verification_code))
        return

    commonutils.send_multipart_email('email/verification',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'username': username,
                                         'verification_code': verification_code,
                                         'site_url': settings.PLATFORM_HOST,
                                     },
                                     'Verify Your Email Address with Helium', [email])


@app.task
def send_registration_email(email):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Welcome email not sent.')
        return

    commonutils.send_multipart_email('email/register',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'site_url': settings.PLATFORM_HOST
                                     },
                                     'Welcome to Helium', [email])


@app.task
def send_password_reset_email(email, temp_password):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Reset password: {}'.format(temp_password))
        return

    metricutils.increment('task.user.password-reset')

    commonutils.send_multipart_email('email/forgot',
                                     {
                                         'password': temp_password,
                                         'site_url': settings.PLATFORM_HOST,
                                     },
                                     'Your Helium Password Has Been Reset', [email])
