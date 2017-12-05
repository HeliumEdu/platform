"""
Asynchronous tasks to be performed.
"""

from __future__ import absolute_import

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.template import Context
from django.template.loader import get_template

from conf.celery import app

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def send_verification_email(email, username, verification_code, platform_host):
    plaintext = get_template('email/verification.txt')
    html = get_template('email/verification.html')
    c = Context({'PROJECT_NAME': settings.PROJECT_NAME,
                 'username': username,
                 'verification_code': verification_code,
                 'site_url': 'http://{}'.format(platform_host)})
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Verify Your Email Address with Helium', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@app.task
def send_verification_text(phone, phone_carrier, phone_verification_code):
    logger.info('Sending verification code to {}@{}'.format(phone, phone_carrier))

    send_mail('Verify Your Phone', 'Enter this verification code on Helium\'s "Settings" page: {}'.format(phone_verification_code), settings.DEFAULT_FROM_EMAIL,
              ['{}@{}'.format(phone, phone_carrier)])


@app.task
def send_registration_email(email, platform_host):
    plaintext = get_template('email/register.txt')
    html = get_template('email/register.html')
    c = Context({'PROJECT_NAME': settings.PROJECT_NAME,
                 'site_url': 'http://{}'.format(platform_host)})
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Welcome to Helium', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email], bcc=[settings.ADMIN_EMAIL_ADDRESS])
    msg.attach_alternative(html_content, "text/html")
    msg.send()


@app.task
def send_password_reset_email(email, temp_password, platform_host):
    plaintext = get_template('email/forgot.txt')
    html = get_template('email/forgot.html')
    c = Context({'password': temp_password,
                 'site_url': 'http://{}'.format(platform_host)})
    text_content = plaintext.render(c)
    html_content = html.render(c)

    msg = EmailMultiAlternatives('Your Helium Password Has Been Reset', text_content,
                                 settings.DEFAULT_FROM_EMAIL, [email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()
