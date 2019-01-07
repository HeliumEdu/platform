import logging

from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import metricutils
from helium.importexport.services import importservice

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


@app.task
def import_example_schedule(user_id):
    try:
        user = get_user_model().objects.get(pk=user_id)
    except get_user_model().DoesNotExist:
        logger.info('User {} does not exist. Nothing to do.'.format(user_id))

        return

    importservice.import_example_schedule(user)

    metricutils.increment('task.user.example-imported')
