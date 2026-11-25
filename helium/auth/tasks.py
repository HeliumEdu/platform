import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth import get_user_model

from django.db import DatabaseError, IntegrityError, OperationalError, transaction
from django.db.models import Count, Q
from django.utils import translation
from django.utils.translation import gettext
from firebase_admin import auth as firebase_auth
from oauth2_provider.models import clear_expired
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from conf.celery import app
from helium.auth.models import UserClientActivity, UserPushToken, UserSettings
from helium.auth.services import nightlymetricsservice
from helium.auth.utils.userutils import dormant_warning_subject, is_staff_user
from helium.common.periodic import register_periodic
from helium.common.services import analyticsservice, cumulativeuserservice, metricsampleservice
from helium.common.utils import commonutils, metricutils, redisutils, taskutils
from helium.common.utils.commonutils import clear_ses_suppression_if_exists, redact_email
from helium.planner.handlers.signals import suppress_cascade_recalculation
from helium.planner.models import Attachment, Homework, Reminder

logger = logging.getLogger(__name__)


@app.task(bind=True)
def clear_email_suppression(self, email):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("ses.suppression.clear", priority="high", published_at_ms=published_at_ms)

    clear_ses_suppression_if_exists(email)

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_verification_email(self, email, verification_code, clear_suppression=False):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.verification.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Verification code: {verification_code}')
        metricutils.task_stop(metrics, value=0)
        return

    if clear_suppression:
        clear_ses_suppression_if_exists(email)

    with translation.override(UserSettings.objects.language_for_email(email)):
        commonutils.send_multipart_email('email/verification',
                                         {
                                             'email': email,
                                             'verification_code': verification_code,
                                             'verify_url': f"{settings.PROJECT_APP_HOST}/verify",
                                         },
                                         gettext('Verify Your Email Address with Helium'), [email],
                                         email_type='verification')

    logger.debug(f"Verification email sent to {redact_email(email)}")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_analytics_event(self, user_id, name, params=None, user_properties=None):
    """
    Asynchronously emit a GA4 event via the Measurement Protocol for the given user. Best-effort:
    swallows failures downstream so analytics delivery never blocks the triggering request.
    """
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start(f'analytics.event.{name}', priority='low', published_at_ms=published_at_ms)

    try:
        user = UserModel.objects.get(pk=user_id)
    except UserModel.DoesNotExist:
        logger.warning(f'send_analytics_event: user {user_id} not found, skipping event {name}')
        metricutils.task_stop(metrics, value=0)
        return

    analyticsservice.send_event(user, name, params=params, user_properties=user_properties)

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_registration_email(self, email):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.registration.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Welcome email not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    with translation.override(UserSettings.objects.language_for_email(email)):
        commonutils.send_multipart_email('email/register',
                                         {
                                             'login_url': f"{settings.PROJECT_APP_HOST}/signin",
                                         },
                                         gettext('Welcome to Helium'), [email],
                                         email_type='registration')

    logger.debug(f"Registration email sent to {redact_email(email)}")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_password_reset_email(self, email, reset_url):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.password-reset.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning(f'Emails disabled. Reset URL: {reset_url}')
        metricutils.task_stop(metrics, value=0)
        return

    clear_ses_suppression_if_exists(email)

    with translation.override(UserSettings.objects.language_for_email(email)):
        commonutils.send_multipart_email('email/forgot',
                                         {
                                             'reset_url': reset_url,
                                             'support_url': settings.SUPPORT_URL,
                                         },
                                         gettext('Reset Your Helium Password'), [email],
                                         email_type='password_reset')

    logger.debug(f"Password reset email sent to {redact_email(email)}")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def delete_user(self, user_id):
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.delete", priority="low", published_at_ms=published_at_ms)
    if settings.SENTRY_ENABLED:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})

    user = None
    try:
        user = UserModel.objects.get(pk=user_id)
    except UserModel.DoesNotExist:
        logger.info(f'User {user_id} does not exist. Nothing to do.')
        metricutils.task_stop(metrics, value=0)
        return

    outstanding_tokens = list(OutstandingToken.objects.filter(user=user))
    blacklisted_tokens = list(BlacklistedToken.objects.filter(token__user=user))

    try:
        firebase_user = firebase_auth.get_user_by_email(user.email)
        firebase_auth.delete_user(firebase_user.uid)
        logger.info(f'Deleted Firebase Auth user for user {user.pk}')
    except firebase_auth.UserNotFoundError:
        logger.info(f'No Firebase Auth user found for user {user.pk}')
    except Exception as e:
        logger.warning(f'Failed to delete Firebase Auth user for user {user.pk}: {str(e)}')
        metricutils.increment('external.firebase.failed', extra_tags=['operation:delete_user'])

    Attachment.objects.filter(user=user).delete()
    Reminder.objects.filter(user=user).delete()

    with suppress_cascade_recalculation(), transaction.atomic():
        cumulativeuserservice.record_deleted_user(user)
        user.delete()

    for token in outstanding_tokens + blacklisted_tokens:
        try:
            token.delete()
        except IntegrityError:
            logger.info('Skipping, token is already deleted.')

    metricutils.task_stop(metrics, user=user, value=1)


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
        expires_at__lte=datetime.now().replace(tzinfo=timezone.utc)).delete()

    metricutils.task_stop(metrics, value=num_deleted)


@app.task(bind=True)
def purge_oauth_tokens(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("token.oauth.purge", priority="low", published_at_ms=published_at_ms)

    clear_expired()

    metricutils.task_stop(metrics)


@app.task(bind=True)
def purge_push_tokens(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("push.token.purge", priority="low", published_at_ms=published_at_ms)

    cutoff = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=settings.PUSH_TOKEN_TTL_DAYS)
    _, num_deleted = UserPushToken.objects.filter(updated_at__lt=cutoff).delete()

    metricutils.task_stop(metrics, value=num_deleted)


@app.task(bind=True)
def sweep_dangling_users(self):
    """
    Nightly cleanup for two classes of dangling users:

    1. Never-verified users past `UNVERIFIED_USER_TTL_DAYS` — enqueue `delete_user`.
    2. Stuck pending-delete accounts — the async `delete_user` task raised or was lost but the
       row is still reserved. Re-queues `delete_user` for each; if it fails again, the unhandled
       exception propagates through CeleryIntegration to Sentry.
    """
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.dangling.purge", priority="low", published_at_ms=published_at_ms)

    num_purged = 0
    for user in UserModel.objects.never_verified():
        logger.info(
            f'Deleting user {user.pk}, never verified or activated after {settings.UNVERIFIED_USER_TTL_DAYS} days.')

        taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)

        num_purged += 1

    stuck_users = list(UserModel.objects.stuck_pending_delete())
    if stuck_users:
        logger.warning(f'Found {len(stuck_users)} stuck pending-delete user(s); re-queuing.')
        for user in stuck_users:
            taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)
            logger.info(f'Re-queued delete_user for stuck user {user.pk}')

    metricsampleservice.record_gauge('users.pending_delete.stuck', len(stuck_users))
    metricutils.task_stop(metrics, value=num_purged)


@app.task(bind=True)
def emit_queue_depth(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("metrics.queue-depth", priority="high", published_at_ms=published_at_ms)

    try:
        queue_depths = redisutils.get_celery_queue_depths()
        for priority, depth in queue_depths.items():
            metricutils.gauge('celery.queue.depth', depth, extra_tags=[f'priority:{priority}'])
        metricutils.cloudwatch_gauge('CeleryHighPriorityQueueDepth', queue_depths['high'])
        logger.debug(f"Emitted queue depths: {queue_depths}")
    except Exception as e:
        logger.warning(f"Failed to get queue depth: {e}")
        raise

    metricutils.task_stop(metrics)


@app.task(bind=True)
def emit_online_users(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("metrics.online-users", priority="low", published_at_ms=published_at_ms)

    for staff_tag in ('true', 'false'):
        count = metricutils.count_online_users(staff_tag)
        metricutils.gauge('users.online', count, extra_tags=[f'staff:{staff_tag}'])
    logger.debug("Emitted online users")

    metricutils.task_stop(metrics)


@app.task(bind=True, soft_time_limit=settings.NIGHTLY_METRICS_TASK_SOFT_TIME_LIMIT,
          time_limit=settings.NIGHTLY_METRICS_TASK_TIME_LIMIT)
def emit_nightly_metrics(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("metrics.nightly", priority="low", published_at_ms=published_at_ms)

    nightlymetricsservice.emit_nightly_metrics()

    metricutils.task_stop(metrics)


@app.task(bind=True)
def rollup_client_activity(self):
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.client-activity.rollup", priority="low", published_at_ms=published_at_ms)

    now = datetime.now().replace(tzinfo=timezone.utc)
    today = now.date()

    try:
        cutoff_90d = today - timedelta(days=90)

        # Prune rows outside the max window
        _, num_pruned = UserClientActivity.objects.filter(date__lt=cutoff_90d).delete()
        if num_pruned:
            logger.info(f'Pruned {num_pruned} UserClientActivity row(s) older than 90 days')

        # Rollup per-user mobile app usage and emit DataDog gauges
        windows = [('7d', 7), ('30d', 30), ('90d', 90)]

        users_with_activity = list(
            UserClientActivity.objects
            .filter(date__gte=cutoff_90d,
                    client__in=(UserClientActivity.CLIENT_WEB, UserClientActivity.CLIENT_MOBILE_APP))
            .values_list('user_id', flat=True)
            .distinct()
        )

        mobile_days_by_user = {
            row['user_id']: row
            for row in (UserClientActivity.objects
                        .filter(date__gte=cutoff_90d, client=UserClientActivity.CLIENT_MOBILE_APP)
                        .values('user_id')
                        .annotate(**{f'days_{days}': Count('pk', filter=Q(date__gte=today - timedelta(days=days)))
                                     for _, days in windows}))
        }

        to_update = []
        percents_by_cohort = defaultdict(list)
        for user in UserModel.objects.filter(pk__in=users_with_activity):
            staff_tag = 'true' if is_staff_user(user) else 'false'
            mobile_days = mobile_days_by_user.get(user.pk, {})

            for window_tag, days in windows:
                percent = mobile_days.get(f'days_{days}', 0) / days * 100
                metricutils.gauge('users.mobile_app_usage_percent', percent,
                                  extra_tags=[f'window:{window_tag}', f'staff:{staff_tag}', f'user:{user.pk}'])
                percents_by_cohort[(window_tag, staff_tag)].append(percent)

                if window_tag == '30d':
                    user.mobile_app_usage_percent_30d = percent

            to_update.append(user)

        if to_update:
            UserModel.objects.bulk_update(to_update, ['mobile_app_usage_percent_30d'])

        for (window_tag, staff_tag), percents in percents_by_cohort.items():
            metricsampleservice.store_summary('users.mobile_app_usage_percent', percents,
                                              extra_tags=[f'window:{window_tag}', f'staff:{staff_tag}'])

        metricutils.task_stop(metrics, value=len(to_update))
        logger.info(f'Client activity rollup complete: {len(to_update)} user(s) updated')

    except Exception as e:
        logger.error(f'Failed to rollup client activity: {e}', exc_info=True)
        raise


def _count_by_latest_app_platform(user_ids):
    """
    Count users by the platform of their most recently updated app push token (`ios` or `android`), or `unknown`
    when they have none.
    """
    latest_platform_by_user = {}
    for user_id, platform in (UserPushToken.objects
                              .filter(user_id__in=user_ids, platform__in=settings.APP_CLIENT_PLATFORMS)
                              .order_by('user_id', 'updated_at')
                              .values_list('user_id', 'platform')):
        latest_platform_by_user[user_id] = platform

    counts = {platform: 0 for platform in sorted(settings.APP_CLIENT_PLATFORMS)} | {'unknown': 0}
    for user_id in user_ids:
        counts[latest_platform_by_user.get(user_id, 'unknown')] += 1

    return counts


@app.task(bind=True)
def evaluate_review_prompts(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.review-prompt.evaluate", priority="low", published_at_ms=published_at_ms)

    try:
        eligible = list(UserSettings.objects.eligible_for_review_prompt().values_list('pk', 'user_id'))

        users_with_completions = set(
            Homework.objects
            .filter(completed=True,
                    course__course_group__example_schedule=False,
                    course__course_group__user_id__in=[user_id for _, user_id in eligible])
            .values_list('course__course_group__user_id', flat=True)
            .distinct())

        flagged = [(user_settings_id, user_id) for user_settings_id, user_id in eligible
                   if user_id in users_with_completions]

        if flagged:
            UserSettings.objects.filter(pk__in=[user_settings_id for user_settings_id, _ in flagged]) \
                .update(prompt_for_review=True)

        flagged_by_platform = _count_by_latest_app_platform([user_id for _, user_id in flagged])
        for platform, count in flagged_by_platform.items():
            metricutils.increment('action.review_prompt.flagged', value=count, extra_tags=[f'client_os:{platform}'])

        metricutils.task_stop(metrics, value=len(eligible))
        logger.info(f"Evaluated {len(eligible)} user(s) for review prompt, flagged {len(flagged)}")

    except Exception as e:
        logger.error(f'Failed to evaluate review prompts: {e}', exc_info=True)
        raise


@app.task(bind=True)
def send_dormant_user_warning_email(self, user_id):
    """Send a dormancy warning email to a user and increment their warning count."""
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.dormant-warning.sent", priority="low", published_at_ms=published_at_ms)

    if settings.SENTRY_ENABLED:
        import sentry_sdk
        sentry_sdk.set_user({"id": user_id})

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Dormant warning email not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    try:
        user = UserModel.objects.get(pk=user_id)
    except UserModel.DoesNotExist:
        logger.info(f'User {user_id} does not exist. Skipping dormant warning email.')
        metricutils.task_stop(metrics, value=0)
        return

    warning_number = user.deletion_warning_count + 1
    if warning_number > 4:
        logger.warning(f'User {user_id} already has {user.deletion_warning_count} warnings. Skipping.')
        metricutils.task_stop(metrics, value=0)
        return

    days_remaining = settings.DORMANT_USER_WARNING_DAYS[warning_number - 1]
    is_final_warning = warning_number == 4

    try:
        with translation.override(user.settings.language):
            subject = dormant_warning_subject(warning_number, days_remaining)
            commonutils.send_multipart_email(
                'email/dormant_warning',
                {
                    'subject': subject,
                    'days_remaining': days_remaining,
                    'dormancy_years': settings.DORMANT_USER_THRESHOLD_YEARS,
                    'is_final_warning': is_final_warning,
                    'login_url': f"{settings.PROJECT_APP_HOST}/signin",
                    'export_url': f'{settings.SUPPORT_URL}import-export-and-backup/importing-and-exporting-your-data/',
                    'delete_account_url': f'{settings.SUPPORT_URL}account/deleting-your-account-and-data/',
                    'support_url': settings.SUPPORT_URL,
                },
                subject,
                [user.email],
                email_type='dormant_warning',
            )

        user.deletion_warning_count = warning_number
        user.deletion_warning_sent_at = datetime.now().replace(tzinfo=timezone.utc)
        user.save(update_fields=['deletion_warning_count', 'deletion_warning_sent_at'])

        logger.info(f'Sent dormant warning email #{warning_number} to user {user_id}')
        metricutils.task_stop(metrics)

    except commonutils.EmailSuppressedException:
        logger.info(f'Email undeliverable for user {user_id}, queuing for deletion')
        taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)
        metricutils.task_stop(metrics, value=0)

    except Exception as e:
        logger.error(f'Failed to send dormant warning email to user {user_id}: {e}', exc_info=True)
        raise


@app.task(bind=True)
def process_dormant_users(self):
    """Process dormant users: send warning emails and delete accounts that have received all warnings."""
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.dormant.process", priority="low", published_at_ms=published_at_ms)

    max_per_run = settings.DORMANT_USER_PURGE_MAX_PER_RUN
    rate_per_sec = settings.EMAIL_SEND_RATE_PER_SEC

    num_warnings_sent = 0
    num_deletions_queued = 0
    total_queued = 0

    def get_stagger_delay(index):
        return index / rate_per_sec

    try:
        warning_users = UserModel.objects.needs_dormancy_warning()
        for user in warning_users:
            if total_queued >= max_per_run:
                logger.info(f'Reached max per run ({max_per_run}), stopping.')
                break
            taskutils.safe_apply_async(
                send_dormant_user_warning_email,
                args=(user.pk,),
                countdown=get_stagger_delay(total_queued),
                priority=settings.CELERY_PRIORITY_LOW
            )
            num_warnings_sent += 1
            total_queued += 1
            logger.info(f'Queued dormant warning #{user.deletion_warning_count + 1} for user {user.pk}')

        if total_queued < max_per_run:
            deletion_users = UserModel.objects.fully_warned()
            for user in deletion_users:
                if total_queued >= max_per_run:
                    logger.info(f'Reached max per run ({max_per_run}), stopping.')
                    break
                taskutils.safe_apply_async(
                    delete_user,
                    args=(user.pk,),
                    countdown=get_stagger_delay(total_queued),
                    priority=settings.CELERY_PRIORITY_LOW
                )
                num_deletions_queued += 1
                total_queued += 1
                logger.info(f'Queued deletion for dormant user {user.pk}')

        metricutils.task_stop(metrics, value=num_warnings_sent + num_deletions_queued)
        metricutils.gauge('users.dormant.warnings_sent', num_warnings_sent)
        metricutils.gauge('users.dormant.deletions_queued', num_deletions_queued)
        metricutils.gauge('users.dormant.operations', num_warnings_sent, extra_tags=['operation:warning'])
        metricutils.gauge('users.dormant.operations', num_deletions_queued, extra_tags=['operation:deletion'])

    except Exception as e:
        logger.error(f'Failed to process dormant users: {e}', exc_info=True)
        raise


register_periodic(purge_refresh_tokens, settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Purge expired refresh tokens")
register_periodic(purge_oauth_tokens, settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Purge expired OAuth tokens")
register_periodic(purge_push_tokens, settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Purge stale push tokens")
register_periodic(emit_queue_depth, 60,
                  priority=settings.CELERY_PRIORITY_HIGH,
                  manually_triggerable=False)
register_periodic(emit_online_users, 60,
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
register_periodic(sweep_dangling_users, crontab(hour=2, minute=0),
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Sweep and retry stuck pending-delete users")
register_periodic(emit_nightly_metrics, crontab(hour=3, minute=0),
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Emit nightly metrics")
register_periodic(rollup_client_activity, crontab(hour=3, minute=30),
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Roll up daily client activity")
register_periodic(evaluate_review_prompts, crontab(hour=4, minute=0),
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Evaluate which users should be prompted for app store review")
register_periodic(process_dormant_users, settings.PROCESS_DORMANT_USERS_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
