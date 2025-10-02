__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import metricutils
from helium.importexport.services import importservice

logger = logging.getLogger(__name__)


@app.task
def import_example_schedule(user_id):
    metrics = metricutils.task_start("import_example_schedule")

    try:
        user = get_user_model().objects.get(pk=user_id)
    except get_user_model().DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        return

    importservice.import_example_schedule(user)

    metricutils.increment('task.user.example-imported', user=user)

    metricutils.task_stop(metrics)
