__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import datetime, timedelta, timezone

from celery.schedules import crontab
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Count, Exists, OuterRef, Q
from firebase_admin import auth as firebase_auth
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from conf.celery import app
from helium.auth.models import UserClientActivity, UserPushToken, UserSettings
from helium.auth.utils.userutils import is_staff_user, rollup_power_users
from helium.common.periodic import register_periodic
from helium.common.services import analyticsservice
from helium.common.utils import commonutils, metricutils, redisutils, taskutils
from helium.common.utils.commonutils import clear_ses_suppression_if_exists, redact_email
from helium.feed.models import ExternalCalendar
from helium.planner.models import Attachment, Category, Course, CourseGroup, Event, Homework, Material, Note, Reminder

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

    commonutils.send_multipart_email('email/verification',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'email': email,
                                         'verification_code': verification_code,
                                         'verify_url': f"{settings.PROJECT_APP_HOST}/verify",
                                     },
                                     'Verify Your Email Address with Helium', [email],
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

    commonutils.send_multipart_email('email/register',
                                     {
                                         'PROJECT_NAME': settings.PROJECT_NAME,
                                         'login_url': f"{settings.PROJECT_APP_HOST}/signin",
                                     },
                                     'Welcome to Helium', [email],
                                     email_type='registration')

    logger.debug(f"Registration email sent to {redact_email(email)}")

    metricutils.task_stop(metrics)


@app.task(bind=True)
def send_password_reset_email(self, email, temp_password):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("email.password-reset.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_EMAILS:
        logger.warning('Emails disabled. Password reset email not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    clear_ses_suppression_if_exists(email)

    commonutils.send_multipart_email('email/forgot',
                                     {
                                         'password': temp_password,
                                         'settings_url': f"{settings.PROJECT_APP_HOST}/settings",
                                         'support_url': settings.SUPPORT_URL,
                                         'status_url': settings.STATUS_URL
                                     },
                                     'Your Helium Password Has Been Reset', [email],
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

        Attachment.objects.filter(user=user).delete()
        Reminder.objects.filter(user=user).delete()

        user.delete()

        for token in outstanding_tokens + blacklisted_tokens:
            try:
                token.delete()
            except IntegrityError:
                logger.info('Skipping, token is already deleted.')

        value = 1
    except (UserModel.DoesNotExist, IntegrityError):
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
        expires_at__lte=datetime.now().replace(tzinfo=timezone.utc)).delete()

    metricutils.task_stop(metrics, value=num_deleted)


@app.task(bind=True)
def purge_push_tokens(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("push.token.purge", priority="low", published_at_ms=published_at_ms)

    cutoff = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=settings.PUSH_TOKEN_TTL_DAYS)
    _, num_deleted = UserPushToken.objects.filter(updated_at__lt=cutoff).delete()

    metricutils.task_stop(metrics, value=num_deleted)


@app.task(bind=True)
def sweep_dangling_users(self):
    """Nightly cleanup for two classes of dangling users:

    1. Never-verified users past `UNVERIFIED_USER_TTL_DAYS` — enqueue `delete_user`.
    2. Stuck pending-delete accounts — the async `delete_user` task raised or was lost but the
       row is still reserved. This is a rare case (usually indicates a real bug), so rather than
       silently retry, notify support so a human can investigate. The email is a digest so the
       admin doesn't get spammed if several accounts are stuck simultaneously.
    """
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.dangling.purge", priority="low", published_at_ms=published_at_ms)

    now = datetime.now().replace(tzinfo=timezone.utc)

    num_purged = 0
    for user in UserModel.objects.filter(
            is_active=False,
            deletion_requested_at__isnull=True,
            created_at__lte=now - timedelta(days=settings.UNVERIFIED_USER_TTL_DAYS)):
        logger.info(
            f'Deleting user {user.pk}, never verified or activated after {settings.UNVERIFIED_USER_TTL_DAYS} days.')

        taskutils.safe_apply_async(delete_user, args=(user.pk,), priority=settings.CELERY_PRIORITY_LOW)

        num_purged += 1

    stuck_users = list(UserModel.objects.filter(
        deletion_requested_at__lte=now - timedelta(minutes=10),
    ))
    if stuck_users:
        logger.warning(f'Found {len(stuck_users)} stuck pending-delete user(s); notifying support.')

        lines = [
            f'- user {u.pk} ({redact_email(u.email)}) requested at {u.deletion_requested_at.isoformat()}'
            for u in stuck_users
        ]
        body = (
            f'{len(stuck_users)} user account(s) have been stuck in pending-delete state, meaning '
            f'the cascade-delete task failed, and at least some data still exists for this user. '
            f'Log in and manually delete these users to complete the process, or investigate if the '
            f'manual delete also fails.\n'
            + '\n'.join(lines)
        )

        send_mail(
            subject=f'[{settings.ENVIRONMENT}] {len(stuck_users)} stuck pending-delete user(s)',
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMIN_EMAIL_ADDRESS],
            fail_silently=False,
        )

    metricutils.gauge('users.pending_delete.stuck', len(stuck_users))
    metricutils.task_stop(metrics, value=num_purged)


@app.task(bind=True)
def emit_queue_depth(self):
    try:
        queue_depth = redisutils.get_redis_client().llen('celery')
        metricutils.gauge('celery.queue.depth', queue_depth)
        logger.debug(f"Emitted queue depth: {queue_depth}")
    except Exception as e:
        logger.warning(f"Failed to get queue depth: {e}")


def _emit_per_entity_distribution(metric, qs, group_field, all_entity_ids, tags):
    """Emit one distribution sample per entity ID, zero-filling for entities absent from qs."""
    counts = dict(
        qs.values(group_field).annotate(c=Count('pk')).values_list(group_field, 'c')
    )
    for entity_id in all_entity_ids:
        metricutils.distribution(metric, counts.get(entity_id, 0), extra_tags=tags)


def _count_distinct_feed_slugs(days, staff_tag, end_date):
    try:
        keys = [
            f'feeds:active_slugs:{staff_tag}:{(end_date - timedelta(days=d)).isoformat()}'
            for d in range(days)
        ]
        return len(redisutils.get_redis_client().sunion(keys))
    except Exception:
        logger.warning("Failed to count distinct feed slugs from Redis", exc_info=True)
        return 0


@app.task(bind=True)
def emit_nightly_metrics(self):
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("metrics.nightly", priority="low", published_at_ms=published_at_ms)

    staff_filter = Q(is_superuser=True) | Q(email__endswith='@heliumedu.com') | Q(email__endswith='@heliumedu.dev')

    # Active users by window
    try:
        for window_tag, days in [('1d', 1), ('7d', 7), ('30d', 30), ('90d', 90), ('180d', 180)]:
            cutoff = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=days)
            base_qs = UserModel.objects.filter(
                is_active=True,
                last_activity__gte=cutoff
            )
            for staff_tag, qs_filter in [('true', staff_filter), ('false', ~staff_filter)]:
                count = base_qs.filter(qs_filter).count()
                metricutils.gauge('users.active', count, extra_tags=[f'window:{window_tag}', f'staff:{staff_tag}'])
            logger.debug(f"Emitted active users ({window_tag})")
    except Exception as e:
        logger.error(f"Failed to emit nightly metrics: {e}", exc_info=True)
        metricutils.task_failure("metrics.nightly", exception_type=type(e).__name__)
        raise

    try:
        now_utc = datetime.now().replace(tzinfo=timezone.utc)

        for window_tag, days in [('1d', 1), ('7d', 7), ('30d', 30), ('90d', 90), ('180d', 180)]:
            cutoff = now_utc - timedelta(days=days)
            base_qs = UserModel.objects.filter(is_active=True, last_activity__gte=cutoff)

            for staff_tag, qs_filter in [('true', staff_filter), ('false', ~staff_filter)]:
                active_qs = base_qs.filter(qs_filter)
                user_ids = list(active_qs.values_list('pk', flat=True))
                total_users = len(user_ids)
                window_staff_tags = [f'window:{window_tag}', f'staff:{staff_tag}']

                if total_users == 0:
                    continue

                course_qs = Course.objects.filter(
                    course_group__user__in=user_ids,
                    course_group__example_schedule=False,
                )
                course_ids = list(course_qs.values_list('pk', flat=True))

                cg_qs = CourseGroup.objects.filter(user__in=user_ids, example_schedule=False)
                cg_ids = list(cg_qs.values_list('pk', flat=True))

                hw_qs = Homework.objects.filter(
                    course__in=course_qs,
                    course__course_group__example_schedule=False,
                )

                _emit_per_entity_distribution('users.data.homework_per_course',
                                              hw_qs, 'course_id', course_ids, window_staff_tags)

                _emit_per_entity_distribution('users.data.homework_per_user',
                                              hw_qs, 'course__course_group__user_id', user_ids,
                                              window_staff_tags)

                _emit_per_entity_distribution('users.data.courses_per_group',
                                              course_qs, 'course_group_id', cg_ids, window_staff_tags)

                _emit_per_entity_distribution('users.data.events_per_user',
                                              Event.objects.filter(
                                                  user__in=user_ids,
                                                  example_schedule=False,
                                              ),
                                              'user_id', user_ids, window_staff_tags)

                _emit_per_entity_distribution('users.data.external_calendars_per_user',
                                              ExternalCalendar.objects.filter(
                                                  user__in=user_ids,
                                                  example_schedule=False,
                                              ),
                                              'user_id', user_ids, window_staff_tags)

                note_qs = Note.objects.filter(
                    user__in=user_ids,
                    example_schedule=False,
                )
                _emit_per_entity_distribution('users.data.notes_per_user',
                                              note_qs, 'user_id', user_ids, window_staff_tags)
                has_homework = Exists(Homework.objects.filter(notes_set=OuterRef('pk')))
                has_event = Exists(Event.objects.filter(notes_set=OuterRef('pk')))
                has_resource = Exists(Material.objects.filter(notes_set=OuterRef('pk')))
                for entity_tag, entity_filter in [
                    ('homework', has_homework),
                    ('event', ~has_homework & has_event),
                    ('resource', ~has_homework & ~has_event & has_resource),
                    ('standalone', ~has_homework & ~has_event & ~has_resource),
                ]:
                    _emit_per_entity_distribution('users.data.notes_per_user',
                                                  note_qs.filter(entity_filter), 'user_id',
                                                  user_ids,
                                                  window_staff_tags + [f'entity:{entity_tag}'])

                reminder_qs = Reminder.objects.filter(user__in=user_ids).exclude(
                    Q(homework__course__course_group__example_schedule=True) |
                    Q(event__example_schedule=True) |
                    Q(course__course_group__example_schedule=True)
                )
                _emit_per_entity_distribution('users.data.reminders_per_user',
                                              reminder_qs, 'user_id', user_ids, window_staff_tags)
                for entity_tag, entity_filter in [
                    ('homework', Q(homework__isnull=False)),
                    ('event', Q(event__isnull=False)),
                    ('course', Q(course__isnull=False)),
                ]:
                    _emit_per_entity_distribution('users.data.reminders_per_user',
                                                  reminder_qs.filter(entity_filter), 'user_id',
                                                  user_ids,
                                                  window_staff_tags + [f'entity:{entity_tag}'])

                _emit_per_entity_distribution('users.data.graded_homework_per_course',
                                              hw_qs.exclude(current_grade=''), 'course_id',
                                              course_ids, window_staff_tags)

                attachment_qs = Attachment.objects.filter(user__in=user_ids).exclude(
                    Q(course__course_group__example_schedule=True) |
                    Q(event__example_schedule=True) |
                    Q(homework__course__course_group__example_schedule=True)
                )
                _emit_per_entity_distribution('users.data.attachments_per_user',
                                              attachment_qs, 'user_id', user_ids,
                                              window_staff_tags)
                for entity_tag, entity_filter in [
                    ('homework', Q(homework__isnull=False)),
                    ('event', Q(event__isnull=False)),
                    ('course', Q(course__isnull=False)),
                ]:
                    _emit_per_entity_distribution('users.data.attachments_per_user',
                                                  attachment_qs.filter(entity_filter), 'user_id',
                                                  user_ids,
                                                  window_staff_tags + [f'entity:{entity_tag}'])

                _emit_per_entity_distribution('users.data.resources_per_user',
                                              Material.objects.filter(
                                                  material_group__user__in=user_ids,
                                                  material_group__example_schedule=False,
                                              ),
                                              'material_group__user_id', user_ids,
                                              window_staff_tags)

                for adoption_metric, adoption_filter in [
                    ('grade_tracking', Exists(Category.objects.filter(
                        course__course_group__user=OuterRef('pk'),
                        course__course_group__example_schedule=False,
                    ))),
                    ('external_calendars', Exists(ExternalCalendar.objects.filter(
                        user=OuterRef('pk'),
                        example_schedule=False,
                    ))),
                    ('notebook', Exists(Note.objects.filter(
                        user=OuterRef('pk'),
                        example_schedule=False,
                    ))),
                    ('resources', Exists(Material.objects.filter(
                        material_group__user=OuterRef('pk'),
                        material_group__example_schedule=False,
                    ))),
                    ('reminders', Exists(Reminder.objects.filter(
                        user=OuterRef('pk'),
                        sent=False,
                    ).exclude(
                        Q(homework__course__course_group__example_schedule=True) |
                        Q(event__example_schedule=True) |
                        Q(course__course_group__example_schedule=True)
                    ))),
                    ('attachments', Exists(Attachment.objects.filter(
                        user=OuterRef('pk'),
                    ).exclude(
                        Q(course__course_group__example_schedule=True) |
                        Q(event__example_schedule=True) |
                        Q(homework__course__course_group__example_schedule=True)
                    ))),
                ]:
                    adopters = active_qs.filter(adoption_filter).count()
                    metricutils.gauge(f'users.adoption.{adoption_metric}.pct',
                                      adopters / total_users * 100,
                                      extra_tags=window_staff_tags)

                feed_adopters = _count_distinct_feed_slugs(days, staff_tag, now_utc.date())
                metricutils.gauge('users.adoption.feeds.pct',
                                  feed_adopters / total_users * 100,
                                  extra_tags=window_staff_tags)

            logger.debug(f"Emitted data richness and adoption metrics ({window_tag})")
    except Exception as e:
        logger.error(f"Failed to emit data richness/adoption metrics: {e}", exc_info=True)
        metricutils.task_failure("metrics.nightly.richness", exception_type=type(e).__name__)
        raise

    try:
        cutoff_30d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=30)
        cutoff_14d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=14)
        today = datetime.now().replace(tzinfo=timezone.utc).date()

        for staff_tag, qs_filter in [('true', staff_filter), ('false', ~staff_filter)]:
            active_qs = UserModel.objects.filter(
                is_active=True,
                last_activity__gte=cutoff_30d,
            ).filter(qs_filter)
            user_ids = list(active_qs.values_list('pk', flat=True))
            total_users = len(user_ids)
            staff_tags = [f'staff:{staff_tag}']

            if total_users == 0:
                continue

            course_qs = Course.objects.filter(
                course_group__user__in=user_ids,
                course_group__example_schedule=False,
            )
            hw_qs = Homework.objects.filter(
                course__in=course_qs,
                course__course_group__example_schedule=False,
            )

            _emit_per_entity_distribution('users.engagement.completions_per_user',
                                          hw_qs.filter(completed=True, completed_at__gte=cutoff_14d),
                                          'course__course_group__user_id', user_ids, staff_tags)

            _emit_per_entity_distribution('users.engagement.graded_homework_per_user',
                                          hw_qs.exclude(current_grade=''),
                                          'course__course_group__user_id', user_ids, staff_tags)

            active_course_adopters = active_qs.filter(
                Exists(Course.objects.filter(
                    course_group__user=OuterRef('pk'),
                    course_group__example_schedule=False,
                    course_group__start_date__lte=today,
                    course_group__end_date__gte=today,
                ))
            ).count()
            metricutils.gauge('users.engagement.has_active_courses.pct',
                              active_course_adopters / total_users * 100,
                              extra_tags=staff_tags)

        logger.debug("Emitted engagement quality metrics")
    except Exception as e:
        logger.error(f"Failed to emit engagement quality metrics: {e}", exc_info=True)
        metricutils.task_failure("metrics.nightly.engagement", exception_type=type(e).__name__)
        raise

    try:
        promoted, cleared = rollup_power_users(UserModel, staff_filter)
        logger.info(f'Power user rollup: {promoted} tagged, {cleared} cleared')
    except Exception as e:
        logger.error(f"Failed to rollup power users: {e}", exc_info=True)
        metricutils.task_failure("metrics.nightly.power_users", exception_type=type(e).__name__)
        raise

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
        users_with_activity = (
            UserClientActivity.objects
            .filter(date__gte=cutoff_90d)
            .values_list('user_id', flat=True)
            .distinct()
        )

        to_update = []
        for user_id in users_with_activity:
            user = UserModel.objects.filter(pk=user_id).first()
            if not user:
                continue

            staff_tag = 'true' if is_staff_user(user) else 'false'

            for window_tag, days in [('7d', 7), ('30d', 30), ('90d', 90)]:
                cutoff = today - timedelta(days=days)
                mobile_days = UserClientActivity.objects.filter(user_id=user_id, date__gte=cutoff, client=UserClientActivity.CLIENT_MOBILE_APP).count()
                percent = mobile_days / days * 100
                metricutils.gauge('users.mobile_app_usage_percent', percent,
                                  extra_tags=[f'window:{window_tag}', f'staff:{staff_tag}', f'user:{user_id}'])

                if window_tag == '30d':
                    user.mobile_app_usage_percent_30d = percent

            to_update.append(user)

        if to_update:
            UserModel.objects.bulk_update(to_update, ['mobile_app_usage_percent_30d'])

        metricutils.task_stop(metrics, value=len(to_update))
        logger.info(f'Client activity rollup complete: {len(to_update)} user(s) updated')

    except Exception as e:
        logger.error(f'Failed to rollup client activity: {e}', exc_info=True)
        metricutils.task_failure("user.client-activity.rollup", exception_type=type(e).__name__, priority="low")
        raise


@app.task(bind=True)
def evaluate_review_prompts(self):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.review-prompt.evaluate", priority="low", published_at_ms=published_at_ms)

    now = datetime.now().replace(tzinfo=timezone.utc)

    try:
        candidates = UserSettings.objects.select_related('user').filter(
            user__is_active=True,
            prompt_for_review=False,
            next_review_prompt_date__isnull=False,
            next_review_prompt_date__lte=now,
            review_prompts_requested__lt=settings.REVIEW_PROMPT_MAX_REQUESTED,
        )

        recent_cutoff = now - timedelta(days=settings.REVIEW_PROMPT_RECENT_WINDOW_DAYS)

        to_update = []
        for user_settings in candidates:
            threshold = settings.REVIEW_PROMPT_HOMEWORK_THRESHOLD * (user_settings.review_prompts_requested + 1)
            base_qs = Homework.objects.for_user(user_settings.user.pk).filter(
                completed=True,
                course__course_group__example_schedule=False,
            )
            total_completed = base_qs.count()
            recent_completed = base_qs.filter(completed_at__gte=recent_cutoff).count()
            if total_completed >= threshold and recent_completed >= settings.REVIEW_PROMPT_RECENT_HOMEWORK_THRESHOLD:
                user_settings.prompt_for_review = True
                to_update.append(user_settings)

        if to_update:
            UserSettings.objects.bulk_update(to_update, ['prompt_for_review'])

        metricutils.task_stop(metrics, value=len(to_update))
        logger.info(f"Review prompt evaluation complete: {len(to_update)} user(s) flagged")

    except Exception as e:
        logger.error(f'Failed to evaluate review prompts: {e}', exc_info=True)
        metricutils.task_failure("user.review-prompt.evaluate", exception_type=type(e).__name__, priority="low")
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
    subject_map = {
        1: f'Your Account Will Be Deleted in {days_remaining} Days',
        2: f'Reminder: {days_remaining} Days Until Account Deletion',
        3: f'Reminder: Only {days_remaining} Days Left',
        4: 'Final Notice: Account Deletion Tomorrow',
    }
    subject = subject_map[warning_number]

    try:
        commonutils.send_multipart_email(
            'email/dormant_warning',
            {
                'subject': subject,
                'days_remaining': days_remaining,
                'dormancy_years': settings.DORMANT_USER_THRESHOLD_YEARS,
                'is_final_warning': is_final_warning,
                'login_url': f"{settings.PROJECT_APP_HOST}/signin",
                'export_url': f'{settings.SUPPORT_URL}/import-export-and-backup/using-exports-to-backup-data-move-between-accounts',
                'delete_account_url': f'{settings.SUPPORT_URL}/account/deleting-your-account-and-data',
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
        metricutils.task_failure("email.dormant-warning.sent", exception_type=type(e).__name__, priority="low")
        raise


@app.task(bind=True)
def process_dormant_users(self):
    """Process dormant users: send warning emails and delete accounts that have received all warnings."""
    UserModel = get_user_model()

    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("user.dormant.process", priority="low", published_at_ms=published_at_ms)

    now = datetime.now().replace(tzinfo=timezone.utc)
    dormancy_cutoff = now - timedelta(days=settings.DORMANT_USER_THRESHOLD_YEARS * 365)
    warning_days = settings.DORMANT_USER_WARNING_DAYS
    max_per_run = settings.DORMANT_USER_PURGE_MAX_PER_RUN
    rate_per_sec = settings.EMAIL_SEND_RATE_PER_SEC

    warning_intervals = {i + 1: warning_days[i] - warning_days[i + 1] for i in range(len(warning_days) - 1)}

    num_warnings_sent = 0
    num_deletions_queued = 0
    total_queued = 0

    def get_stagger_delay(index):
        return index / rate_per_sec

    try:
        dormancy_filter = Q(is_active=True, last_activity__lte=dormancy_cutoff)

        needs_warning = Q(deletion_warning_count=0)
        for count, interval_days in warning_intervals.items():
            needs_warning |= Q(
                deletion_warning_count=count,
                deletion_warning_sent_at__lte=now - timedelta(days=interval_days)
            )

        warning_users = UserModel.objects.filter(dormancy_filter & needs_warning)
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
            deletion_users = UserModel.objects.filter(
                is_active=True,
                last_activity__lte=dormancy_cutoff,
                deletion_warning_count__gte=4,
            )
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
        metricutils.task_failure("user.dormant.process", exception_type=type(e).__name__, priority="low")
        raise


register_periodic(purge_refresh_tokens, settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Purge expired refresh tokens")
register_periodic(purge_push_tokens, settings.REFRESH_TOKEN_PURGE_FREQUENCY_SEC,
                  priority=settings.CELERY_PRIORITY_LOW,
                  description="Purge stale push tokens")
register_periodic(emit_queue_depth, 60,
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
register_periodic(sweep_dangling_users, crontab(hour=2, minute=0),
                  priority=settings.CELERY_PRIORITY_LOW,
                  manually_triggerable=False)
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
