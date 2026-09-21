import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from conf.celery import app
from helium.common import enums
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
            # Lives here, not in the service: a task owns its process, a request does not
            with importservice.suppress_post_save_signals():
                importservice.import_example_schedule(user)

        user.settings.setup_state = enums.SETUP_COMPLETE
        user.settings.save(update_fields=['setup_state', 'updated_at'])

        metricutils.timing("user.setup.total_duration", _setup_elapsed_ms(user))

        value = 1
    except UserModel.DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        value = 0

    metricutils.task_stop(metrics, user=user, value=value)


def _setup_elapsed_ms(user):
    """
    Time from when the app took over provisioning the account until now. That is the login that handed the
    user to the setup screen (OAuth creation or email verification), or creation for legacy clients that start
    setup at registration before ever logging in.
    """
    handoff_at = user.last_login or user.created_at

    return int((timezone.now() - handoff_at).total_seconds() * 1000)
