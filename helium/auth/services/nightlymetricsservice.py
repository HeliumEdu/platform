import logging
from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, F, OuterRef, Q

from helium.auth.utils.userutils import rollup_power_users
from helium.common import enums
from helium.common.services import cumulativeuserservice, metricsampleservice
from helium.common.utils import redisutils
from helium.feed.models import ExternalCalendar
from helium.planner.models import Attachment, Course, CourseGroup, CourseSchedule, Event, Homework, \
    Resource, Note, Reminder

logger = logging.getLogger(__name__)


def emit_nightly_metrics():
    UserModel = get_user_model()

    staff_ids = list(UserModel.objects.staff().values_list('pk', flat=True))
    staff_cohorts = [('true', lambda qs: qs.filter(pk__in=staff_ids)),
                     ('false', lambda qs: qs.exclude(pk__in=staff_ids))]

    # Active users by window
    try:
        for window_tag, days in [('1d', 1), ('7d', 7), ('30d', 30), ('90d', 90), ('180d', 180)]:
            cutoff = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=days)
            base_qs = UserModel.objects.filter(
                is_active=True,
                last_activity__gte=cutoff
            )
            for staff_tag, select_cohort in staff_cohorts:
                count = select_cohort(base_qs).count()
                metricsampleservice.record_gauge('users.active', count,
                                                 extra_tags=[f'window:{window_tag}', f'staff:{staff_tag}'])
            logger.debug(f"Emitted active users ({window_tag})")
    except Exception as e:
        logger.error(f"Failed to emit nightly metrics: {e}", exc_info=True)
        raise

    try:
        cumulativeuserservice.record_cumulative_users()
        logger.debug("Emitted cumulative users")
    except Exception as e:
        logger.error(f"Failed to emit cumulative user metrics: {e}", exc_info=True)
        raise

    try:
        now_utc = datetime.now().replace(tzinfo=timezone.utc)

        for window_tag, days in [('1d', 1), ('7d', 7), ('30d', 30), ('90d', 90), ('180d', 180)]:
            cutoff = now_utc - timedelta(days=days)
            base_qs = UserModel.objects.filter(is_active=True, last_activity__gte=cutoff)

            for staff_tag, select_cohort in staff_cohorts:
                active_qs = select_cohort(base_qs)
                user_ids = list(active_qs.values_list('pk', flat=True))
                total_users = len(user_ids)
                window_staff_tags = [f'window:{window_tag}', f'staff:{staff_tag}']

                if total_users == 0:
                    continue

                _emit_data_richness_metrics(user_ids, window_staff_tags)

                _emit_adoption_metrics(active_qs, total_users, window_staff_tags, days, staff_tag, now_utc)

            logger.debug(f"Emitted data richness and adoption metrics ({window_tag})")
    except Exception as e:
        logger.error(f"Failed to emit data richness/adoption metrics: {e}", exc_info=True)
        raise

    try:
        _emit_engagement_quality_metrics(UserModel, staff_cohorts)

        logger.debug("Emitted engagement quality metrics")
    except Exception as e:
        logger.error(f"Failed to emit engagement quality metrics: {e}", exc_info=True)
        raise

    try:
        promoted, cleared = rollup_power_users(UserModel)
        logger.info(f'Power user rollup: {promoted} tagged, {cleared} cleared')
    except Exception as e:
        logger.error(f"Failed to rollup power users: {e}", exc_info=True)
        raise


def _emit_per_entity_distribution(metric, qs, group_field, all_entity_ids, tags):
    """Emit one distribution sample per entity ID, zero-filling for entities absent from qs."""
    counts = dict(
        qs.values(group_field).annotate(c=Count('pk')).values_list(group_field, 'c')
    )
    metricsampleservice.record_distribution(metric, [counts.get(entity_id, 0) for entity_id in all_entity_ids],
                                            extra_tags=tags)


def _changed_since_example_import(user_path):
    imported_at = f'{user_path}__example_schedule_first_imported_at'
    return Q(**{f'{imported_at}__isnull': True}) | Q(updated_at__gt=F(imported_at))


def _reminder_item_changed_since_example_import():
    imported_at = F('user__example_schedule_first_imported_at')
    return (Q(user__example_schedule_first_imported_at__isnull=True) |
            Q(homework__updated_at__gt=imported_at) |
            Q(event__updated_at__gt=imported_at) |
            Q(course__updated_at__gt=imported_at))


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


def _emit_data_richness_metrics(user_ids, window_staff_tags):
    course_qs = Course.objects.filter(
        course_group__user__in=user_ids,
        course_group__example_schedule=False,
    ).filter(_changed_since_example_import('course_group__user'))
    course_ids = list(course_qs.values_list('pk', flat=True))

    cg_qs = CourseGroup.objects.filter(
        user__in=user_ids,
        example_schedule=False,
    ).filter(_changed_since_example_import('user'))
    cg_ids = list(cg_qs.values_list('pk', flat=True))

    hw_qs = Homework.objects.filter(
        course__course_group__user__in=user_ids,
        course__course_group__example_schedule=False,
    ).filter(_changed_since_example_import('course__course_group__user'))

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
                                  ).filter(_changed_since_example_import('user')),
                                  'user_id', user_ids, window_staff_tags)

    _emit_per_entity_distribution('users.data.external_calendars_per_user',
                                  ExternalCalendar.objects.filter(
                                      user__in=user_ids,
                                      example_schedule=False,
                                  ).filter(_changed_since_example_import('user')),
                                  'user_id', user_ids, window_staff_tags)

    schedule_qs = CourseSchedule.objects.filter(
        course__course_group__user__in=user_ids,
        course__course_group__example_schedule=False,
    ).filter(_changed_since_example_import('course__course_group__user')).meeting()
    _emit_per_entity_distribution('users.data.schedules_per_user',
                                  schedule_qs, 'course__course_group__user_id', user_ids,
                                  window_staff_tags)
    for entity_tag, entity_filter in [
        ('weekly', Q(cycle_length__isnull=True, is_week_based=False)),
        ('cycle', Q(cycle_length__isnull=False)),
        ('week_based', Q(is_week_based=True)),
    ]:
        _emit_per_entity_distribution('users.data.schedules_per_user',
                                      schedule_qs.filter(entity_filter),
                                      'course__course_group__user_id', user_ids,
                                      window_staff_tags + [f'entity:{entity_tag}'])

    note_qs = Note.objects.filter(
        user__in=user_ids,
        example_schedule=False,
    ).filter(_changed_since_example_import('user'))
    _emit_per_entity_distribution('users.data.notes_per_user',
                                  note_qs, 'user_id', user_ids, window_staff_tags)
    has_homework = Exists(Homework.objects.filter(notes_set=OuterRef('pk')))
    has_event = Exists(Event.objects.filter(notes_set=OuterRef('pk')))
    has_resource = Exists(Resource.objects.filter(notes_set=OuterRef('pk')))
    has_course = Exists(Course.objects.filter(notes_set=OuterRef('pk')))
    for entity_tag, entity_filter in [
        ('homework', has_homework),
        ('event', ~has_homework & has_event),
        ('resource', ~has_homework & ~has_event & has_resource),
        ('course', ~has_homework & ~has_event & ~has_resource & has_course),
        ('standalone', ~has_homework & ~has_event & ~has_resource & ~has_course),
    ]:
        _emit_per_entity_distribution('users.data.notes_per_user',
                                      note_qs.filter(entity_filter), 'user_id',
                                      user_ids,
                                      window_staff_tags + [f'entity:{entity_tag}'])

    reminder_qs = Reminder.objects.filter(user__in=user_ids).exclude(
        Q(homework__course__course_group__example_schedule=True) |
        Q(event__example_schedule=True) |
        Q(course__course_group__example_schedule=True)
    ).filter(_reminder_item_changed_since_example_import())
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
                                  hw_qs.graded(), 'course_id',
                                  course_ids, window_staff_tags)

    attachment_qs = Attachment.objects.filter(user__in=user_ids).exclude(
        Q(course__course_group__example_schedule=True) |
        Q(event__example_schedule=True) |
        Q(homework__course__course_group__example_schedule=True) |
        Q(resource__resource_group__example_schedule=True)
    )
    _emit_per_entity_distribution('users.data.attachments_per_user',
                                  attachment_qs, 'user_id', user_ids,
                                  window_staff_tags)
    for entity_tag, entity_filter in [
        ('homework', Q(homework__isnull=False)),
        ('event', Q(event__isnull=False)),
        ('course', Q(course__isnull=False)),
        ('resource', Q(resource__isnull=False)),
    ]:
        _emit_per_entity_distribution('users.data.attachments_per_user',
                                      attachment_qs.filter(entity_filter), 'user_id',
                                      user_ids,
                                      window_staff_tags + [f'entity:{entity_tag}'])

    _emit_per_entity_distribution('users.data.resources_per_user',
                                  Resource.objects.filter(
                                      resource_group__user__in=user_ids,
                                      resource_group__example_schedule=False,
                                  ).filter(_changed_since_example_import('resource_group__user')),
                                  'resource_group__user_id', user_ids,
                                  window_staff_tags)


def _emit_adoption_metrics(active_qs, total_users, window_staff_tags, days, staff_tag, now_utc):
    adopter_counts = {}
    for adoption_metric, adoption_filter in [
        ('class_schedules', Exists(CourseSchedule.objects.filter(
            course__course_group__user=OuterRef('pk'),
            course__course_group__example_schedule=False,
        ).filter(_changed_since_example_import('course__course_group__user')).meeting())),
        ('rotating_schedules', Exists(CourseSchedule.objects.filter(
            course__course_group__user=OuterRef('pk'),
            course__course_group__example_schedule=False,
        ).filter(_changed_since_example_import('course__course_group__user')).rotating())),
        ('grade_tracking', Exists(Homework.objects.graded().filter(
            course__course_group__user=OuterRef('pk'),
            course__course_group__example_schedule=False,
        ).filter(_changed_since_example_import('course__course_group__user')))),
        ('gpa', Exists(Homework.objects.graded().filter(
            course__course_group__user=OuterRef('pk'),
            course__course_group__example_schedule=False,
            course__credits__gt=0,
        ).exclude(course__grade_point=enums.NO_GRADE).filter(
            _changed_since_example_import('course__course_group__user')))),
        ('external_calendars', Exists(ExternalCalendar.objects.filter(
            user=OuterRef('pk'),
            example_schedule=False,
        ).filter(_changed_since_example_import('user')))),
        ('notebook', Exists(Note.objects.filter(
            user=OuterRef('pk'),
            example_schedule=False,
        ).filter(_changed_since_example_import('user')))),
        ('resources', Exists(Resource.objects.filter(
            resource_group__user=OuterRef('pk'),
            resource_group__example_schedule=False,
        ).filter(_changed_since_example_import('resource_group__user')))),
        ('reminders', Exists(Reminder.objects.filter(
            user=OuterRef('pk'),
            sent=False,
        ).exclude(
            Q(homework__course__course_group__example_schedule=True) |
            Q(event__example_schedule=True) |
            Q(course__course_group__example_schedule=True)
        ).filter(_reminder_item_changed_since_example_import()))),
        ('attachments', Exists(Attachment.objects.filter(
            user=OuterRef('pk'),
        ).exclude(
            Q(course__course_group__example_schedule=True) |
            Q(event__example_schedule=True) |
            Q(homework__course__course_group__example_schedule=True) |
            Q(resource__resource_group__example_schedule=True)
        ))),
    ]:
        adopters = active_qs.filter(adoption_filter).count()
        adopter_counts[adoption_metric] = adopters
        metricsampleservice.record_gauge(f'users.adoption.{adoption_metric}.pct',
                                         adopters / total_users * 100,
                                         extra_tags=window_staff_tags)

    scheduled_users = adopter_counts['class_schedules']
    if scheduled_users:
        metricsampleservice.record_gauge('users.adoption.rotating_schedules.of_scheduled.pct',
                                         adopter_counts['rotating_schedules'] / scheduled_users * 100,
                                         extra_tags=window_staff_tags)

    feed_adopters = _count_distinct_feed_slugs(days, staff_tag, now_utc.date())
    metricsampleservice.record_gauge('users.adoption.feeds.pct',
                                     feed_adopters / total_users * 100,
                                     extra_tags=window_staff_tags)


def _emit_engagement_quality_metrics(UserModel, staff_cohorts):
    cutoff_30d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=30)
    cutoff_14d = datetime.now().replace(tzinfo=timezone.utc) - timedelta(days=14)
    today = datetime.now().replace(tzinfo=timezone.utc).date()

    for staff_tag, select_cohort in staff_cohorts:
        active_qs = select_cohort(UserModel.objects.filter(
            is_active=True,
            last_activity__gte=cutoff_30d,
        ))
        user_ids = list(active_qs.values_list('pk', flat=True))
        total_users = len(user_ids)
        staff_tags = [f'staff:{staff_tag}']

        if total_users == 0:
            continue

        hw_qs = Homework.objects.filter(
            course__course_group__user__in=user_ids,
            course__course_group__example_schedule=False,
        ).filter(_changed_since_example_import('course__course_group__user'))

        _emit_per_entity_distribution('users.engagement.completions_per_user',
                                      hw_qs.filter(completed=True, completed_at__gte=cutoff_14d),
                                      'course__course_group__user_id', user_ids, staff_tags)

        _emit_per_entity_distribution('users.engagement.graded_homework_per_user',
                                      hw_qs.graded(),
                                      'course__course_group__user_id', user_ids, staff_tags)

        active_course_adopters = active_qs.filter(
            Exists(Course.objects.filter(
                course_group__user=OuterRef('pk'),
                course_group__example_schedule=False,
                course_group__start_date__lte=today,
                course_group__end_date__gte=today,
            ).filter(_changed_since_example_import('course_group__user')))
        ).count()
        metricsampleservice.record_gauge('users.engagement.has_active_courses.pct',
                                         active_course_adopters / total_users * 100,
                                         extra_tags=staff_tags)
