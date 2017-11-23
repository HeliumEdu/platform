"""
Celery tasks.
"""

from __future__ import absolute_import

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

from conf.celery import app

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

logger = logging.getLogger(__name__)


@app.task
def send_contact_email(subject, name, email, body):
    msg = EmailMultiAlternatives(
            'Contact Form: ' + subject,
            'Name: ' + name + '<br />Email: ' + email + '<br /><br />Body: ' + body,
            'noreply@dentiful.com',
            [settings.DEFAULT_FROM_EMAIL]
    )
    msg.content_subtype = "html"
    msg.send()
