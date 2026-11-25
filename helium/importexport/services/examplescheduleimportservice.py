import json
import logging
import os
from contextlib import contextmanager
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from helium.common import enums, errorcodes
from helium.common.utils import gradeutils, metricutils
from helium.feed.models import ExternalCalendar
from helium.planner.models import CourseGroup, Course, CourseSchedule, Homework, Event, Category, Reminder, \
    ResourceGroup, Resource
from helium.importexport.services import examplescheduleguardservice
from helium.planner.services import gradingservice
from helium.importexport.services.importservice import ImportedSchedule, import_notes
from helium.importexport.services.scheduleshiftservice import shift_schedule_to_month

logger = logging.getLogger(__name__)

_SUPPRESSED_SIGNALS = frozenset({Course, CourseSchedule, Category, Homework, Event})

_RESOURCES = os.path.join(os.path.dirname(__file__), '..', 'resources')


@contextmanager
def suppress_post_save_signals():
    """
    Skip the per-row grade and reminder recalculations an import makes redundant.

    Swaps the process-wide receiver list, so every thread sees it. Safe only where the caller owns
    the process, as a prefork Celery worker does; never use it to serve a request.
    """
    sender_ids = {id(s) for s in _SUPPRESSED_SIGNALS}
    original_receivers = post_save.receivers
    post_save.receivers = [
        item for item in original_receivers
        if not (isinstance(item[0], tuple) and len(item[0]) >= 2 and item[0][1] in sender_ids)
    ]
    post_save.sender_receivers_cache.clear()
    try:
        yield
    finally:
        post_save.receivers = original_receivers
        post_save.sender_receivers_cache.clear()


def example_schedule_path(language):
    """
    The example schedule written in the given language: ``example_schedule.<language>.json``, falling back to the
    English ``example_schedule.json``.
    """
    translated = os.path.join(_RESOURCES, f'example_schedule.{language}.json')
    return translated if os.path.exists(translated) else os.path.join(_RESOURCES, 'example_schedule.json')


def import_example_schedule(user):
    with open(example_schedule_path(user.settings.language), 'rb') as f:
        json_str = f.read().decode('utf-8')

    try:
        data = json.loads(json_str)

        # Fixture-internal, never read by the nominal import path.
        source_time_zone = data.get('time_zone')
        if source_time_zone:
            source_tz = ZoneInfo(source_time_zone)
        else:
            source_tz = None
            logger.warning('Example schedule declares no time_zone, leaving class times as authored')

        with transaction.atomic():
            examplescheduleguardservice.promote_modified(user.pk)

            imported = _bulk_import_example_schedule(data, user)

            shift_schedule_to_month(user, -1, imported, source_tz)

            for category_id in Category.objects.for_user(user.pk).values_list('pk', flat=True):
                gradingservice.recalculate_category_grade(category_id)

            course_group_ids = set()
            for course in (Course.objects.for_user(user.pk)
                    .filter(course_group__example_schedule=True)
                    .select_related('course_group')):
                gradingservice.recalculate_course_grade(
                    course.pk, gradeutils.effective_grade_scale(course.grade_scale_template,
                                                                course.course_group.grade_scale))
                course_group_ids.add(course.course_group_id)

            for course_group_id in course_group_ids:
                gradingservice.recalculate_course_group_grade(course_group_id)

            user.example_schedule_imported_at = timezone.now()
            if user.example_schedule_first_imported_at is None:
                user.example_schedule_first_imported_at = user.example_schedule_imported_at
            get_user_model().objects.filter(pk=user.pk).update(
                example_schedule_imported_at=user.example_schedule_imported_at,
                example_schedule_first_imported_at=user.example_schedule_first_imported_at)
    except ValueError:
        raise ValidationError({
            'details': 'Invalid JSON.'
        }, code=errorcodes.EXAMPLE_SCHEDULE_INVALID)


@transaction.atomic
def _bulk_import_example_schedule(data, user):
    course_group_remap = {}
    course_remap = {}
    category_remap = {}
    resource_group_remap = {}
    resource_remap = {}
    event_remap = {}
    homework_remap = {}

    # --- CourseGroup ---
    for cg in data.get('course_groups', []):
        instance = CourseGroup.objects.create(
            title=cg['title'],
            start_date=cg['start_date'],
            end_date=cg['end_date'],
            shown_on_calendar=cg.get('shown_on_calendar', True),
            overall_grade=Decimal(cg.get('overall_grade', '-1')),
            trend=cg.get('trend'),
            grade_scale=gradeutils.preset_grade_scale(cg['grade_scale_template']),
            grade_scale_template=cg['grade_scale_template'],
            exceptions=cg.get('exceptions', ''),
            example_schedule=True,
            user=user,
        )
        course_group_remap[cg['id']] = instance.pk

    # --- Course ---
    for c in data.get('courses', []):
        instance = Course.objects.create(
            title=c['title'],
            room=c.get('room', ''),
            credits=Decimal(c.get('credits', '0')),
            color=c.get('color', '#000000'),
            website=c.get('website') or None,
            is_online=c.get('is_online', False),
            current_grade=Decimal(c.get('current_grade', '-1')),
            trend=c.get('trend'),
            teacher_name=c.get('teacher_name', ''),
            teacher_email=c.get('teacher_email') or '',
            start_date=c['start_date'],
            end_date=c['end_date'],
            exceptions=c.get('exceptions', ''),
            course_group_id=course_group_remap[c['course_group']],
        )
        course_remap[c['id']] = instance.pk

    # --- CourseSchedule ---
    schedule_objects = []
    for cs in data.get('course_schedules', []):
        schedule_objects.append(CourseSchedule(
            days_of_week=cs['days_of_week'],
            sun_start_time=cs['sun_start_time'],
            sun_end_time=cs['sun_end_time'],
            mon_start_time=cs['mon_start_time'],
            mon_end_time=cs['mon_end_time'],
            tue_start_time=cs['tue_start_time'],
            tue_end_time=cs['tue_end_time'],
            wed_start_time=cs['wed_start_time'],
            wed_end_time=cs['wed_end_time'],
            thu_start_time=cs['thu_start_time'],
            thu_end_time=cs['thu_end_time'],
            fri_start_time=cs['fri_start_time'],
            fri_end_time=cs['fri_end_time'],
            sat_start_time=cs['sat_start_time'],
            sat_end_time=cs['sat_end_time'],
            exceptions=cs.get('exceptions', ''),
            course_id=course_remap[cs['course']],
        ))
    CourseSchedule.objects.bulk_create(schedule_objects)

    # --- Category ---
    categories = data.get('categories', [])
    Category.objects.bulk_create([
        Category(
            title=cat['title'],
            weight=Decimal(cat.get('weight', '0')),
            color=cat.get('color', '#000000'),
            average_grade=Decimal(cat.get('average_grade', '-1')),
            grade_by_weight=Decimal(cat.get('grade_by_weight', '0')),
            trend=cat.get('trend'),
            course_id=course_remap[cat['course']],
        )
        for cat in categories
    ])
    category_pks_by_key = {
        (course_id, title): pk
        for pk, course_id, title in Category.objects.filter(
            course_id__in=course_remap.values()).values_list('pk', 'course_id', 'title')
    }
    for cat in categories:
        category_remap[cat['id']] = category_pks_by_key[(course_remap[cat['course']], cat['title'])]

    # --- ResourceGroup ---
    for rg in data.get('resource_groups', []):
        instance = ResourceGroup.objects.create(
            title=rg['title'],
            shown_on_calendar=rg.get('shown_on_calendar', True),
            example_schedule=True,
            user=user,
        )
        resource_group_remap[rg['id']] = instance.pk

    # --- Resource (with M2M courses) ---
    ResourceCourseThrough = Resource.courses.through
    m2m_rows = []
    for m in data.get('resources', []):
        instance = Resource.objects.create(
            title=m['title'],
            status=m.get('status', enums.OWNED),
            condition=m.get('condition', enums.BRAND_NEW),
            website=m.get('website') or None,
            price=m.get('price', ''),
            resource_group_id=resource_group_remap[m['resource_group']],
        )
        resource_remap[m['id']] = instance.pk
        for course_id in [course_remap[c] for c in m.get('courses', [])]:
            m2m_rows.append(ResourceCourseThrough(resource_id=instance.pk, course_id=course_id))

    if m2m_rows:
        ResourceCourseThrough.objects.bulk_create(m2m_rows)

    # --- ExternalCalendar ---
    for ec in data.get('external_calendars', []):
        ExternalCalendar.objects.create(
            title=ec['title'],
            url=ec['url'],
            color=ec.get('color', '#000000'),
            shown_on_calendar=ec.get('shown_on_calendar', True),
            example_schedule=True,
            user=user,
        )

    # --- Event ---
    for e in data.get('events', []):
        instance = Event.objects.create(
            title=e['title'],
            all_day=e.get('all_day', False),
            show_end_time=e.get('show_end_time', False),
            start=e['start'],
            end=e['end'],
            priority=e.get('priority', 50),
            owner_id=e.get('owner_id') or None,
            recurrence_rule=e.get('recurrence_rule'),
            exception_dates=e.get('exception_dates'),
            example_schedule=True,
            user=user,
        )
        event_remap[e['id']] = instance.pk

    # --- Homework (individual save for auto-category + completed_at) ---
    hw_resource_m2m = []
    for h in data.get('homework', []):
        instance = Homework(
            title=h['title'],
            all_day=h.get('all_day', False),
            show_end_time=h.get('show_end_time', False),
            start=h['start'],
            end=h['end'],
            priority=h.get('priority', 50),
            current_grade=h.get('current_grade', ''),
            completed=h.get('completed', False),
            category_id=category_remap.get(h['category']) if h.get('category') else None,
            course_id=course_remap[h['course']],
            recurrence_rule=h.get('recurrence_rule'),
            exception_dates=h.get('exception_dates'),
        )
        instance.save()
        homework_remap[h['id']] = instance.pk
        hw_resource_m2m.append((instance.pk, [resource_remap[m] for m in h.get('resources', [])]))

    HomeworkResourceThrough = Homework.resources.through
    hw_m2m_rows = []
    for hw_pk, resource_ids in hw_resource_m2m:
        for resource_id in resource_ids:
            hw_m2m_rows.append(HomeworkResourceThrough(homework_id=hw_pk, resource_id=resource_id))
    if hw_m2m_rows:
        HomeworkResourceThrough.objects.bulk_create(hw_m2m_rows)

    # --- Reminder (individual save for start_of_range computation) ---
    for r in data.get('reminders', []):
        instance = Reminder(
            message=r.get('message', ''),
            offset=r.get('offset', 30),
            offset_type=r.get('offset_type', enums.MINUTES),
            type=r.get('type', enums.PUSH),
            sent=r.get('sent', False),
            dismissed=r.get('dismissed', False),
            homework_id=homework_remap[r['homework']] if r.get('homework') else None,
            event_id=event_remap[r['event']] if r.get('event') else None,
            course_id=course_remap[r['course']] if r.get('course') else None,
            user=user,
        )
        instance.save()

    notes = data.get('notes', [])
    if notes:
        import_notes(notes, user, homework_remap, event_remap, resource_remap, course_remap, example_schedule=True)

    metricutils.increment("user.import.schedule")

    logger.info(
        f"Bulk imported example schedule: {len(course_group_remap)} course groups, "
        f"{len(course_remap)} courses, {len(data.get('course_schedules', []))} schedules, "
        f"{len(category_remap)} categories, {len(resource_group_remap)} resource groups, "
        f"{len(resource_remap)} resources, {len(data.get('external_calendars', []))} external calendars, "
        f"{len(event_remap)} events, "
        f"{len(homework_remap)} homework, {len(data.get('reminders', []))} reminders, "
        f"{len(data.get('notes', []))} notes"
    )

    return ImportedSchedule(
        course_group_remap=course_group_remap,
        course_remap=course_remap,
        category_remap=category_remap,
        resource_group_remap=resource_group_remap,
        resource_remap=resource_remap,
        event_remap=event_remap,
        homework_remap=homework_remap,
    )
