import logging

from django.conf import settings
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from conf.celery import app
from helium.auth.models import UserPushToken, UserSettings
from helium.common.periodic import PERIODIC_TASKS
from helium.common.services.pushservice import send_dismiss, send_notifications
from helium.common.services.sesreputationservice import process_ses_notification
from helium.common.utils import metricutils, taskutils
from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, Event, MaterialGroup, Note

logger = logging.getLogger(__name__)


@app.task(bind=True)
def send_pushes(self, push_tokens, username, subject, message, reminder_data):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("push.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_PUSH:
        logger.warning(
            f'Push disabled. Push with message "{message}" to {username} not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    invalid_tokens = send_notifications(push_tokens, subject, message, reminder_data)

    if invalid_tokens:
        deleted_count, _ = UserPushToken.objects.filter(token__in=invalid_tokens).delete()
        logger.info(f"Removed {deleted_count} invalid push token(s) after send failure")
        metricutils.increment('action.push.token.purged', value=deleted_count)

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_dismiss_pushes(self, push_tokens, reminder_id):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("push.dismiss", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_PUSH:
        metricutils.task_stop(metrics, value=0)
        return

    invalid_tokens = send_dismiss(push_tokens, reminder_id)

    if invalid_tokens:
        deleted_count, _ = UserPushToken.objects.filter(token__in=invalid_tokens).delete()
        logger.info(f"Removed {deleted_count} invalid push token(s) after dismiss send failure")
        metricutils.increment('action.push.token.purged', value=deleted_count)

    metricutils.task_stop(metrics)


@app.task(bind=True)
def process_ses_event(self, message_json):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("ses.event.processed", priority="low", published_at_ms=published_at_ms)

    process_ses_notification(message_json)

    metricutils.task_stop(metrics)


def _example_schedule_remains():
    return (Exists(CourseGroup.objects.filter(user=OuterRef('user_id'), example_schedule=True))
            | Exists(Event.objects.filter(user=OuterRef('user_id'), example_schedule=True))
            | Exists(MaterialGroup.objects.filter(user=OuterRef('user_id'), example_schedule=True))
            | Exists(Note.objects.filter(user=OuterRef('user_id'), example_schedule=True))
            | Exists(ExternalCalendar.objects.filter(user=OuterRef('user_id'), example_schedule=True)))


def reconcile_show_getting_started_async(instance):
    """
    Queue a check for whether `instance` was the last example schedule item.
    """
    if not instance.example_schedule:
        return

    user_id = instance.user_id
    transaction.on_commit(lambda: taskutils.safe_apply_async(reconcile_show_getting_started,
        args=(user_id,), priority=settings.CELERY_PRIORITY_LOW
    ))


@app.task(bind=True)
def reconcile_show_getting_started(self, user_id, retries=0):
    """
    Unset `show_getting_started` once no example schedule items remain.

    Importing the example schedule sets it, and clearing that data through the app unsets it;
    deleting the example items by hand would otherwise leave it set, with the dialog returning
    and re-import disabled.
    """
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.gettingstarted.reconcile", published_at_ms=published_at_ms)

    try:
        cleared = (UserSettings.objects
                   .filter(user_id=user_id, show_getting_started=True)
                   .exclude(_example_schedule_remains())
                   .update(show_getting_started=False, updated_at=timezone.now()))

        if cleared:
            logger.info(f'No example schedule items remain for user {user_id}, unset show_getting_started')

        metricutils.task_stop(metrics, value=cleared)
    except (IntegrityError, OperationalError) as ex:  # pragma: no cover
        taskutils.retry_on_db_error(ex, metrics, reconcile_show_getting_started,
                                    (user_id, retries + 1), retries)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    for spec in PERIODIC_TASKS:
        sig = spec.task.s()
        if spec.priority is not None:
            sig = sig.set(priority=spec.priority)
        sender.add_periodic_task(spec.schedule, sig)
