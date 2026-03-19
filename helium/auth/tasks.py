__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import datetime, timedelta

import pytz
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken
from firebase_admin import auth as firebase_auth

from celery.schedules import crontab

from conf.celery import app
from helium.common.utils import commonutils, metricutils

logger = logging.getLogger(__name__)


@app.task(bind=True)
def send_verification_email(self, email, username, verification_code):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.verification.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Verification code: {verification_code}')
        metricutils.task_stop(metrics, value=0)
        return

    commonutils.send_multipart_email('email/verification',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'email': email,
                                         'verification_code': verification_code,
                                         'verify_url': f"{settings.PROJECT_APP_HOST}/verify",
                                     },
                                     'Verify Your Email Address with Helium', [email])

    logger.debug("Verification email sent successfully")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_registration_email(self, email):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.registration.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Welcome email not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    commonutils.send_multipart_email('email/register',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'login_url': f"{settings.PROJECT_APP_HOST}/login",
                                     },
                                     'Welcome to Helium', [email])

    logger.debug(f"Registration email sent successfully")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_password_reset_email(self, email, temp_password):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.password-reset.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Password reset email not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    commonutils.send_multipart_email('email/forgot',
                                     {
                                         'password': temp_password,
                                         'settings_url': f"{settings.PROJECT_APP_HOST}/settings",
                                         'support_url': settings.SUPPORT_URL,
                                         'status_url': settings.STATUS_URL
                                     },
                                     'Your Helium Password Has Been Reset', [email])

    logger.debug(f"Password reset email sent successfully")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def delete_user(self, user_id):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.delete", priority="low", published_at_ms=published_at_ms)
    if settings.SENTRY_ENABLED:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})

    # The instance may no longer exist by the time this request is processed, in which case we can simply and safely
    # skip it
    user = None
    try:
        user = get_user_model().objects.get(pk=user_id)

        outstanding_tokens = list(OutstandingToken.objects.filter(user=user))
        blacklisted_tokens = list(BlacklistedToken.objects.filter(token__user=user))

        # Try to delete Firebase Auth user if they signed in with OAuth (Google, Apple, etc.)
        try:
            firebase_user = firebase_auth.get_user_by_email(user.email)
            firebase_auth.delete_user(firebase_user.uid)
            logger.info(f'Deleted Firebase Auth user for user {user.pk}')
        except firebase_auth.UserNotFoundError:
            logger.info(f'No Firebase Auth user found for user {user.pk}')
        except Exception as e:
            logger.warning(f'Failed to delete Firebase Auth user for user {user.pk}: {str(e)}')
            metricutils.increment('external.firebase.failed', extra_tags=['operation:delete_user'])

        user.delete()

        for token in outstanding_tokens + blacklisted_tokens:
            try:
                token.delete()
            except IntegrityError:
                logger.info('Skipping, token is already deleted.')

        value = 1
    except (get_user_model().DoesNotExist, IntegrityError):
        logger.info(f'User {user_id} does not exist. Nothing to do.')

        value = 0

    metricutils.task_stop(metrics, user=user, value=value)


@app.task(bind=True)
def blacklist_refresh_token(self, token):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("token.refresh.blacklist", priority="low", published_at_ms=published_at_ms)

    try:
        RefreshToken(token).blacklist()
        metricutils.task_stop(metrics)
    except TokenError:
        logger.info('Skipping, token is already blacklisted.')
        metricutils.task_stop(metrics, value=0)


@app.task(bind=True)
def purge_refresh_tokens(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("token.refresh.purge", priority="low", published_at_ms=published_at_ms)

    _, num_deleted = OutstandingToken.objects.filter(
        expires_at__lte=datetime.now().replace(tzinfo=pytz.utc)).delete()

    metricutils.task_stop(metrics, value=num_deleted)


@app.task(bind=True)
def purge_unverified_users(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.unverified.purge", priority="low", published_at_ms=published_at_ms)

    num_purged = 0
    for user in get_user_model().objects.filter(
            is_active=False,
            created_at__lte=datetime.now().replace(tzinfo=pytz.utc) - timedelta(
                days=settings.UNVERIFIED_USER_TTL_DAYS)):
        logger.info(
            f'Deleting user {user.pk}, never verified or activated after {settings.UNVERIFIED_USER_TTL_DAYS} days.')

        delete_user.apply_async(args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)

        num_purged += 1

    metricutils.task_stop(metrics, value=num_purged)


@app.task(bind=True)
def emit_queue_depth(self):
    """Emit the current Celery queue depth as a metric."""
    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL)
        queue_depth = r.llen('celery')
        metricutils.gauge('celery.queue.depth', queue_depth)
        logger.debug(f"Emitted queue depth: {queue_depth}")
    except Exception as e:
        logger.warning(f"Failed to get queue depth: {e}")


@app.task(bind=True)
def emit_nightly_metrics(self):
    """Emit nightly aggregate metrics."""
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("metrics.nightly", priority="low", published_at_ms=published_at_ms)

    try:
        # Active users by window (users with recent login/token refresh activity)
        for window_tag, days in [('1d', 1), ('7d', 7), ('30d', 30), ('90d', 90), ('180d', 180)]:
            cutoff = datetime.now().replace(tzinfo=pytz.utc) - timedelta(days=days)
            count = get_user_model().objects.filter(
                is_active=True,
                last_activity__gte=cutoff
            ).count()
            metricutils.gauge('users.active', count, extra_tags=[f'window:{window_tag}'])
            logger.debug(f"Emitted active users ({window_tag}): {count}")
    except Exception as e:
        logger.error(f"Failed to emit nightly metrics: {e}", exc_info=True)
        metricutils.task_failure("metrics.nightly", exception_type=type(e).__name__)
        raise

    metricutils.task_stop(metrics)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    # Add schedule to check for expired refresh tokens periodically
    sender.add_periodic_task(settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC, purge_refresh_tokens.s())
    # Emit queue depth every minute for monitoring
    sender.add_periodic_task(60, emit_queue_depth.s())
    # Purge unverified users daily at 4am UTC
    sender.add_periodic_task(crontab(hour=4, minute=0), purge_unverified_users.s())
    # Emit nightly aggregate metrics at 3am UTC
    sender.add_periodic_task(crontab(hour=3, minute=0), emit_nightly_metrics.s())
