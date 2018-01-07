import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

from conf.celery import app
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def send_verification_email(email, username, verification_code):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Verification code: {}'.format(verification_code))
        return

    plaintext = get_template('email/verification.txt')
    html = get_template('email/verification.html')
    c = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'username': username,
        'verification_code': verification_code,
        'site_url': settings.PLATFORM_HOST,
    }
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Verify Your Email Address with Helium', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@app.task
def send_registration_email(email):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Welcome email not sent.')
        return

    plaintext = get_template('email/register.txt')
    html = get_template('email/register.html')
    c = {
        'PROJECT_NAME': settings.PROJECT_NAME,
        'site_url': settings.PLATFORM_HOST,
    }
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Welcome to Helium', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email], bcc=[settings.ADMIN_EMAIL_ADDRESS])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@app.task
def send_password_reset_email(email, temp_password):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Reset password: {}'.format(temp_password))
        return

    plaintext = get_template('email/forgot.txt')
    html = get_template('email/forgot.html')
    c = {
        'password': temp_password,
        'site_url': settings.PLATFORM_HOST,
    }
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Your Helium Password Has Been Reset', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    metricutils.increment('task.user.password-reset')
