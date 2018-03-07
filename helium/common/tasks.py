import logging

from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail

from conf.celery import app
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.8'

logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


@app.task
def send_text(phone, phone_carrier, subject, body):
    if settings.DISABLE_EMAILS:
        logger.warning(
            'Emails disabled. Text with subject "{}" to {}@{} not sent.'.format(subject, phone, phone_carrier))
        return

    logger.info('Sending text with subject "{}" to {}@{}'.format(subject, phone, phone_carrier))

    send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, ['{}@{}'.format(phone, phone_carrier)])

    metricutils.increment('task.text.sent')
