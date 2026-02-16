__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import metricutils
from helium.importexport.services import importservice

logger = logging.getLogger(__name__)


@app.task
def import_example_schedule(user_id):
    metrics = metricutils.task_start("user.import.schedule.example")

    user = None
    try:
        user = get_user_model().objects.get(pk=user_id)

        importservice.import_example_schedule(user)

        # Mark setup as complete now that example schedule is imported
        user.settings.is_setup_complete = True
        user.settings.save()

        value = 1
    except get_user_model().DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        value = 0

    metricutils.task_stop(metrics, user=user, value=value)
