__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from conf.celery import app
from helium.common.utils import metricutils
from helium.importexport.services import importservice

logger = logging.getLogger(__name__)


@app.task(bind=True)
def import_example_schedule(self, user_id, example_schedule=True):
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.import.schedule.example", priority="high", published_at_ms=published_at_ms)
    if settings.SENTRY_ENABLED:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})

    user = None
    try:
        user = UserModel.objects.get(pk=user_id)

        if example_schedule:
            importservice.import_example_schedule(user)

        # Mark setup as complete now that example schedule is imported
        user.settings.is_setup_complete = True
        user.settings.save()

        value = 1
    except UserModel.DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        value = 0

    metricutils.task_stop(metrics, user=user, value=value)
