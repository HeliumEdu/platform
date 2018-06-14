import logging

from celery.signals import task_failure

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.21'

logger = logging.getLogger(__name__)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, **kwargs):
    pass
