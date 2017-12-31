import logging

from celery.schedules import crontab

from conf.celery import app

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


@app.task
def email_reminders():
    # TODO: not yet implemented
    pass


@app.task
def text_reminders():
    # TODO: not yet implemented
    pass


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Email reminders every minute
    sender.add_periodic_task(crontab(), email_reminders.s())

    # Text reminders every minute
    sender.add_periodic_task(crontab(), text_reminders.s())
