import logging

from django.conf import settings
from django.core.mail import send_mail

from conf.celery import app

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def send_text(phone, phone_carrier, subject, body):
    if settings.DISABLE_EMAILS:
        logger.warn('Emails disabled. Text with subject "{}" to {}@{} not sent.'.format(subject, phone, phone_carrier))
        return

    logger.info('Sending text with subject "{}" to {}@{}'.format(subject, phone, phone_carrier))

    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, ['{}@{}'.format(phone, phone_carrier)])
