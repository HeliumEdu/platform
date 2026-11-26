import logging
from contextlib import contextmanager
from typing import Dict, NamedTuple

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.settings import api_settings

from helium.common import errorcodes
from helium.common.utils import metricutils, taskutils
from helium.common.utils.validators import validate_recurrence_rule
from helium.feed.serializers.externalcalendarserializer import ExternalCalendarSerializer
from helium.planner.models import CourseGroup, Homework, Category
from helium.importexport.services import legacyimportparity
from helium.planner.serializers.categoryserializer import CategorySerializer
from helium.planner.serializers.coursegroupserializer import CourseGroupSerializer
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer
from helium.planner.serializers.courseserializer import CourseSerializer
from helium.planner.serializers.eventserializer import EventSerializer
from helium.planner.serializers.homeworkserializer import HomeworkSerializer
from helium.planner.serializers.resourcegroupserializer import ResourceGroupSerializer
from helium.planner.serializers.resourceserializer import ResourceSerializer
from helium.planner.serializers.noteserializer import NoteSerializer
from helium.planner.serializers.reminderserializer import ReminderSerializer
from helium.planner.tasks import recalculate_category_grades_for_course

logger = logging.getLogger(__name__)

_SECTIONS_WITH_IDS = (
    'external_calendars', 'course_groups', 'courses', 'course_schedules', 'categories',
    'resource_groups', 'resources', 'events', 'homework', 'reminders', 'notes',
)


class ImportRowValidationError(ValidationError):
    """
    A rejected import's row errors, as messages and also as `row_errors`: one `{section, id, field, message}` per
    message, `field` null when the error isn't about one field.
    """

    def __init__(self, detail, row_errors):
        super().__init__(detail, code=errorcodes.IMPORT_ROW_INVALID)
        self.row_errors = row_errors


def _row_validation_error(section, row_id, errors):
    """
    Flatten a row's serializer errors into messages naming the section and `id` they came from,
    so a bare field name can't be read as belonging to the wrong entity.
    """
    messages = []
    row_errors = []
    for field, field_errors in errors.items():
        for error in (field_errors if isinstance(field_errors, (list, tuple)) else [field_errors]):
            code = error.code if isinstance(error, ErrorDetail) else errorcodes.IMPORT_ROW_INVALID
            if field == api_settings.NON_FIELD_ERRORS_KEY:
                row_field = None
                message = gettext('%(section)s id %(id)s: %(error)s') % {
                    'section': section, 'id': row_id, 'error': error}
            else:
                row_field = field
                message = gettext('%(section)s id %(id)s, %(field)s: %(error)s') % {
                    'section': section, 'id': row_id, 'field': field, 'error': error}
            messages.append(ErrorDetail(message, code=code))
            row_errors.append({'section': section, 'id': row_id, 'field': row_field, 'message': str(error)})

    return ImportRowValidationError({section: messages}, row_errors)


class _SectionErrors:
    """
    Collect every row error in a section, so one 400 lists them all, each naming the row it came from. Later sections
    reference this one's ids, so the import stops at the end of the first section with errors.
    """

    def __init__(self, section):
        self.section = section
        self.messages = []
        self.row_errors = []

    @contextmanager
    def row(self, row_id):
        try:
            yield
        except ValidationError as error:
            detail = dict(error.detail) if isinstance(error.detail, dict) else {'non_field_errors': error.detail}
            own = detail.pop(self.section, [])
            own_messages = own if isinstance(own, list) else [own]
            self.messages.extend(own_messages)
            if isinstance(error, ImportRowValidationError) and not detail:
                self.row_errors.extend(error.row_errors)
            else:
                self.row_errors.extend({'section': self.section, 'id': row_id, 'field': None, 'message': str(message)}
                                       for message in own_messages)
            if detail:
                remainder = _row_validation_error(self.section, row_id, detail)
                self.messages.extend(remainder.detail[self.section])
                self.row_errors.extend(remainder.row_errors)

    def raise_if_any(self):
        if self.messages:
            raise ImportRowValidationError({self.section: self.messages}, self.row_errors)


def _coerce_id(value, section, key='id'):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise ValidationError({section: gettext('Invalid `%(key)s` value: %(value)s is not a valid id.') % {
            'key': key, 'value': repr(value)}},
                              code=errorcodes.IMPORT_ID_INVALID)


def _validate_section_ids(data):
    """
    Pre-pass over the payload to verify all row ids are integer or integer-coercible strings, and
    that ids within a section are unique. Surfaces malformed hand-rolled files as a clean 400.
    """
    for section in _SECTIONS_WITH_IDS:
        rows = data.get(section, []) or []
        if not isinstance(rows, list):
            raise ValidationError({section: gettext('Section `%(section)s` must be a list.') % {'section': section}},
                                  code=errorcodes.IMPORT_SECTION_NOT_LIST)

        seen = set()
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                raise ValidationError({section: gettext('Row %(index)s in `%(section)s` must be an object.') % {
                    'index': index, 'section': section}},
                                      code=errorcodes.IMPORT_ROW_NOT_OBJECT)

            if 'id' not in row:
                raise ValidationError({section: gettext('Row %(index)s in `%(section)s` is missing required key '
                                                        '`id`.') % {'index': index, 'section': section}},
                                      code=errorcodes.IMPORT_ROW_MISSING_ID)

            coerced = _coerce_id(row['id'], section)
            if coerced in seen:
                raise ValidationError({section: gettext('Duplicate id `%(id)s` in `%(section)s`.') % {
                    'id': coerced, 'section': section}},
                                      code=errorcodes.IMPORT_DUPLICATE_ID)
            seen.add(coerced)
            row['id'] = coerced


def _resolve_parent(remap, raw_id, section, parent_key):
    """
    Resolve a parent FK id via the remap dict. Raises ValidationError if the id is missing or
    doesn't resolve — surfaces hand-rolled broken references as 400 rather than letting them
    crash deeper in the stack as IntegrityError → 500.
    """
    if raw_id is None:
        raise ValidationError(
            {section: gettext('Missing required parent reference `%(parent_key)s` in section `%(section)s`.') % {
                'parent_key': parent_key, 'section': section}},
            code=errorcodes.IMPORT_PARENT_MISSING)

    coerced = _coerce_id(raw_id, section, key=parent_key)
    resolved = remap.get(coerced)
    if resolved is None:
        raise ValidationError(
            {section: gettext('Unresolved `%(parent_key)s` reference `%(id)s` in section `%(section)s`.') % {
                'parent_key': parent_key, 'id': coerced, 'section': section}},
            code=errorcodes.UNRESOLVED_REFERENCE)
    return resolved


def _import_external_calendars(external_calendars, user):
    errors = _SectionErrors('external_calendars')
    for external_calendar in external_calendars:
        with errors.row(external_calendar['id']):
            serializer = ExternalCalendarSerializer(data=external_calendar)

            if serializer.is_valid():
                serializer.save(user=user, example_schedule=False)
            else:
                raise _row_validation_error('external_calendars', external_calendar['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(external_calendars)} external calendars.")

    return len(external_calendars)


def _import_course_groups(course_groups, user):
    course_group_remap = {}

    errors = _SectionErrors('course_groups')
    for course_group in course_groups:
        with errors.row(course_group['id']):
            serializer = CourseGroupSerializer(data=course_group)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=False)
                course_group_remap[course_group['id']] = instance.pk
            else:
                raise _row_validation_error('course_groups', course_group['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(course_groups)} course groups.")

    return course_group_remap


def _import_courses(courses, course_group_remap, existing_course_group_id=None):
    course_remap = {}

    errors = _SectionErrors('courses')
    for course in courses:
        with errors.row(course['id']):
            course.pop('template', None)

            course_group_id = existing_course_group_id or _resolve_parent(
                course_group_remap, course.get('course_group'), 'courses', 'course_group')
            course['course_group'] = course_group_id

            serializer = CourseSerializer(data=course)

            if serializer.is_valid():
                instance = serializer.save(course_group_id=course_group_id)
                course_remap[course['id']] = instance.pk
            else:
                raise _row_validation_error('courses', course['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(courses)} courses.")

    return course_remap


def _import_course_schedules(course_schedules, course_remap):
    errors = _SectionErrors('course_schedules')
    for course_schedule in course_schedules:
        with errors.row(course_schedule['id']):
            course_id = _resolve_parent(
                course_remap, course_schedule.get('course'), 'course_schedules', 'course')
            course_schedule['course'] = course_id

            serializer = CourseScheduleSerializer(data=course_schedule)

            if serializer.is_valid():
                serializer.save(course_id=course_id)
            else:
                raise _row_validation_error('course_schedules', course_schedule['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(course_schedules)} course schedules.")

    return len(course_schedules)


def _import_categories(categories, request, course_remap):
    category_remap = {}

    errors = _SectionErrors('categories')
    for category in categories:
        with errors.row(category['id']):
            course_id = _resolve_parent(course_remap, category.get('course'), 'categories', 'course')
            request.parser_context['kwargs']['course'] = course_id

            if category.get('title') == 'Uncategorized':
                category_remap[category['id']] = _merge_uncategorized(category, request, course_id)
                continue

            serializer = CategorySerializer(data=category, context={'request': request})

            if serializer.is_valid():
                instance = serializer.save(course_id=course_id)
                category_remap[category['id']] = instance.pk
            else:
                raise _row_validation_error('categories', category['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(categories)} categories.")

    return category_remap


def _merge_uncategorized(category, request, course_id):
    uncategorized = Category.objects.get_uncategorized(course_id)
    if 'color' in category:
        serializer = CategorySerializer(uncategorized, data={'color': category['color']}, partial=True,
                                        context={'request': request})
        if not serializer.is_valid():
            raise _row_validation_error('categories', category['id'], serializer.errors)
        serializer.save()
    return uncategorized.pk


def _import_resource_groups(resource_groups, user):
    resource_group_remap = {}

    errors = _SectionErrors('resource_groups')
    for resource_group in resource_groups:
        with errors.row(resource_group['id']):
            serializer = ResourceGroupSerializer(data=resource_group)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=False)
                resource_group_remap[resource_group['id']] = instance.pk
            else:
                raise _row_validation_error('resource_groups', resource_group['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(resource_groups)} resource groups.")

    return resource_group_remap


def _import_resources(resources, resource_group_remap, course_remap, user):
    resource_remap = {}

    errors = _SectionErrors('resources')
    for resource in resources:
        with errors.row(resource['id']):
            resource_group_id = _resolve_parent(
                resource_group_remap, resource.get('resource_group'), 'resources', 'resource_group')
            resource['resource_group'] = resource_group_id

            courses = resource.get('courses') or []
            if not isinstance(courses, list):
                raise ValidationError({'resources': gettext('Field `%(field)s` must be a list.') % {
                    'field': 'courses'}},
                                      code=errorcodes.IMPORT_FIELD_NOT_LIST)
            for i, course in enumerate(courses):
                courses[i] = _resolve_parent(course_remap, course, 'resources', 'courses')
            resource['courses'] = courses

            serializer = ResourceSerializer(data=resource)

            if serializer.is_valid():
                instance = serializer.save(resource_group_id=resource_group_id)
                resource_remap[resource['id']] = instance.pk
            else:
                raise _row_validation_error('resources', resource['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(resources)} resources.")

    return resource_remap


def _import_events(events, user):
    event_remap = {}

    errors = _SectionErrors('events')
    for event in events:
        with errors.row(event['id']):
            try:
                validate_recurrence_rule(event.get('recurrence_rule'))
            except DjangoValidationError:
                logger.info(f"Dropping unsupported recurrence rule from imported event {event.get('id')}.")
                event['recurrence_rule'] = None
                event['exception_dates'] = None
            serializer = EventSerializer(data=event)

            if serializer.is_valid():
                instance = serializer.save(user=user, example_schedule=False)
                event_remap[event['id']] = instance.pk
            else:
                raise _row_validation_error('events', event['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(events)} events.")

    return event_remap


def _import_homework(homework, course_remap, category_remap, resource_remap, user):
    homework_remap = {}
    course_by_category = dict(Category.objects.filter(pk__in=category_remap.values()).values_list('pk', 'course_id'))

    errors = _SectionErrors('homework')
    for h in homework:
        with errors.row(h['id']):
            course_id = _resolve_parent(course_remap, h.get('course'), 'homework', 'course')
            h['course'] = course_id

            if h.get('category'):
                h['category'] = _resolve_parent(category_remap, h.get('category'), 'homework', 'category')
                if course_by_category.get(h['category']) != course_id:
                    logger.info(f"Homework {h.get('id')} imported into Uncategorized; its category belongs to another course")
                    h['category'] = None
            else:
                h['category'] = None

            resources = h.get('resources') or []
            if not isinstance(resources, list):
                raise ValidationError({'homework': gettext('Field `%(field)s` must be a list.') % {
                    'field': 'resources'}},
                                      code=errorcodes.IMPORT_FIELD_NOT_LIST)
            for i, resource in enumerate(resources):
                resources[i] = _resolve_parent(resource_remap, resource, 'homework', 'resources')
            h['resources'] = resources

            serializer = HomeworkSerializer(data=h)

            if serializer.is_valid():
                instance = serializer.save(course_id=course_id)
                homework_remap[h['id']] = instance.pk

                # completed_at is read-only (inferred by Homework.save() the first time completed flips true),
                # so the serializer ignores it. Restore the original value from a user's own export rather
                # than letting save() re-stamp it to import time.
                completed_at = parse_datetime(h['completed_at']) if h.get('completed_at') else None
                if completed_at:
                    Homework.objects.filter(pk=instance.pk).update(completed_at=completed_at)
            else:
                raise _row_validation_error('homework', h['id'], serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {len(homework)} homework.")

    return homework_remap


def _import_reminders(reminders, user, event_remap, homework_remap, course_remap):
    seen_active_series = set()
    created = 0
    errors = _SectionErrors('reminders')
    for reminder in reminders:
        with errors.row(reminder.get('id')):
            reminder['homework'] = _resolve_parent(
                homework_remap, reminder.get('homework'), 'reminders', 'homework') \
                if reminder.get('homework') else None
            reminder['event'] = _resolve_parent(
                event_remap, reminder.get('event'), 'reminders', 'event') \
                if reminder.get('event') else None
            reminder['course'] = _resolve_parent(
                course_remap, reminder.get('course'), 'reminders', 'course') \
                if reminder.get('course') else None

            # A course series holds one active reminder; `message` does not distinguish a series.
            if reminder.get('course') and not reminder.get('sent') and not reminder.get('dismissed'):
                series_key = (reminder.get('course'), reminder.get('type'),
                              reminder.get('offset'), reminder.get('offset_type'))
                if series_key in seen_active_series:
                    continue
                seen_active_series.add(series_key)

            serializer = ReminderSerializer(data=reminder)

            if serializer.is_valid():
                serializer.save(user=user)
                created += 1
            else:
                raise _row_validation_error('reminders', reminder.get('id'), serializer.errors)
    errors.raise_if_any()

    logger.info(f"Imported {created} reminders.")

    return created


def import_notes(notes, user, homework_remap, event_remap, resource_remap, course_remap, example_schedule):
    """
    Import notes via NoteSerializer, including those linked to entities. Handles both standalone
    notes and notes linked to homework/events/resources/courses. Entity ids are remapped to
    their newly-created values before serializer validation, so an unresolved id surfaces as a
    clean 400 rather than silently dropping the link.
    """
    notes_count = 0

    errors = _SectionErrors('notes')
    for note_data in notes:
        with errors.row(note_data['id']):
            if not isinstance(note_data, dict):
                raise ValidationError({'notes': gettext('Each note must be an object.')},
                                      code=errorcodes.IMPORT_ROW_NOT_OBJECT)

            payload = {
                'title': note_data.get('title', ''),
                'content': note_data.get('content') or {},
                'homework': [
                    _resolve_parent(homework_remap, raw_id, 'notes', 'homework')
                    for raw_id in (note_data.get('homework') or [])
                ],
                'events': [
                    _resolve_parent(event_remap, raw_id, 'notes', 'events')
                    for raw_id in (note_data.get('events') or [])
                ],
                'resources': [
                    _resolve_parent(resource_remap, raw_id, 'notes', 'resources')
                    for raw_id in (note_data.get('resources') or [])
                ],
                'courses': [
                    _resolve_parent(course_remap, raw_id, 'notes', 'courses')
                    for raw_id in (note_data.get('courses') or [])
                ],
            }

            serializer = NoteSerializer(data=payload)
            if not serializer.is_valid():
                raise _row_validation_error('notes', note_data['id'], serializer.errors)
            serializer.save(user=user, example_schedule=example_schedule)
            notes_count += 1
    errors.raise_if_any()

    logger.info(f"Imported {notes_count} notes.")

    return notes_count


class ImportedSchedule(NamedTuple):
    """
    The remaps one import produced. A user can hold several example schedules, all
    flagged `example_schedule`, so the seed rebase scopes to these rather than to that flag.
    """

    course_group_remap: Dict[int, int]
    course_remap: Dict[int, int]
    category_remap: Dict[int, int]
    resource_group_remap: Dict[int, int]
    resource_remap: Dict[int, int]
    event_remap: Dict[int, int]
    homework_remap: Dict[int, int]

    def ids(self):
        """
        The ids the import assigned, by section (as the API names them), then by the id each row had in the file.
        """
        return {
            'course_groups': self.course_group_remap,
            'courses': self.course_remap,
            'categories': self.category_remap,
            'resource_groups': self.resource_group_remap,
            'resources': self.resource_remap,
            'events': self.event_remap,
            'homework': self.homework_remap,
        }


@transaction.atomic
def import_user(request, data, dry_run=False, course_group_id=None):
    """
    Parse the given JSON string and import its associated data for the given user. Each model will be imported in a
    schema matching that of the documented APIs.

    :param request: The request performing the import.
    :param data: The data that will be imported for the user.
    :param dry_run: Validate the import, then roll it back.
    :param course_group_id: An existing Course Group of the user's to import every Course into, in place of the
                            file's Course Groups (which are not imported).
    :return: The counts imported per section, and the imported schedule (whose `ids()` are the ids assigned, by
             section, then by the id in the file).
    """
    if not isinstance(data, dict):
        raise ValidationError(gettext('Import payload must be a JSON object.'),
                              code=errorcodes.IMPORT_PAYLOAD_NOT_OBJECT)

    legacyimportparity.upgrade_legacy_import(data)

    if course_group_id is not None:
        _verify_course_group_is_users(course_group_id, request.user)
        data['course_groups'] = []

    _validate_section_ids(data)

    external_calendars = data.get('external_calendars', [])
    external_calendar_count = _import_external_calendars(external_calendars, request.user) if external_calendars else 0

    course_groups = data.get('course_groups', [])
    course_group_remap = _import_course_groups(course_groups, request.user) if course_groups else {}

    courses = data.get('courses', [])
    course_remap = _import_courses(courses, course_group_remap, course_group_id) if courses else {}

    course_schedules = data.get('course_schedules', [])
    course_schedules_count = _import_course_schedules(course_schedules, course_remap) if course_schedules else 0

    categories = data.get('categories', [])
    category_remap = _import_categories(categories, request, course_remap) if categories else {}

    resource_groups = data.get('resource_groups', [])
    resource_group_remap = _import_resource_groups(resource_groups, request.user) if resource_groups else {}

    resources = data.get('resources', [])
    resource_remap = _import_resources(resources, resource_group_remap, course_remap,
                                       request.user) if resources else {}

    events = data.get('events', [])
    event_remap = _import_events(events, request.user) if events else {}

    homework = data.get('homework', [])
    homework_remap = _import_homework(homework, course_remap, category_remap, resource_remap,
                                      request.user) if homework else {}

    reminders = data.get('reminders', [])
    reminders_count = _import_reminders(reminders, request.user, event_remap, homework_remap, course_remap) if reminders else 0

    notes = data.get('notes', [])
    notes_count = import_notes(notes, request.user, homework_remap, event_remap, resource_remap, course_remap,
                               example_schedule=False) if notes else 0

    for course_id in set(course_remap.values()):
        transaction.on_commit(lambda course_id=course_id: taskutils.safe_apply_async(
            recalculate_category_grades_for_course, args=(course_id,), priority=settings.CELERY_PRIORITY_LOW))

    transaction.on_commit(lambda: metricutils.increment("user.import.schedule"))

    counts = (external_calendar_count, len(course_group_remap), len(course_remap), course_schedules_count,
              len(category_remap), len(resource_group_remap), len(resource_remap), len(event_remap),
              len(homework_remap), reminders_count, notes_count)

    if dry_run:
        transaction.set_rollback(True)

    return counts, ImportedSchedule(
        course_group_remap=course_group_remap,
        course_remap=course_remap,
        category_remap=category_remap,
        resource_group_remap=resource_group_remap,
        resource_remap=resource_remap,
        event_remap=event_remap,
        homework_remap=homework_remap,
    )


def _verify_course_group_is_users(course_group_id, user):
    if not CourseGroup.objects.for_user(user.pk).filter(pk=course_group_id).exists():
        raise ValidationError({'course_group': gettext('Unresolved `course_group` reference `%(id)s`.') % {
            'id': course_group_id}},
                              code=errorcodes.UNRESOLVED_REFERENCE)
