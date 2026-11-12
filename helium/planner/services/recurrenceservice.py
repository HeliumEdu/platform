import itertools
import logging
from zoneinfo import ZoneInfo

from django.db import transaction
from rest_framework.exceptions import ValidationError

from helium.common import enums
from helium.common.utils import datetimeutils
from helium.common.utils.validators import join_recurrence_rule, normalize_recurrence_rule_for_user, \
    parse_recurrence_rule, shift_recurrence_rule_for_user
from helium.planner.models import Event, Homework
from helium.planner.services import reminderservice

logger = logging.getLogger(__name__)

#: The most occurrences a repeating Homework may have.
MAX_HOMEWORK_OCCURRENCES = 366

_SHARED_FIELDS = ('title', 'all_day', 'show_end_time', 'priority', 'url')

#: What an occurrence keeps from its series when it becomes its own item.
_OCCURRENCE_FIELDS = {
    Event: _SHARED_FIELDS + ('user',),
    Homework: _SHARED_FIELDS + ('course', 'category'),
}


def prepare_write(validated_data, user, instance=None):
    """
    Ready the recurrence in an Event or Homework write: a given rule is normalized against the item's start, a
    moved start moves an unchanged rule and its exceptions with it, and clearing the rule collapses its reminder
    series.

    :param validated_data: The serializer's validated data, updated in place.
    :param user: The item's owner.
    :param instance: The item being updated, or None on create.
    """
    start = validated_data.get('start', instance.start if instance else None)
    if 'recurrence_rule' in validated_data:
        validated_data['recurrence_rule'] = normalize_recurrence_rule_for_user(
            validated_data['recurrence_rule'], start, user) or None
    elif instance is not None and instance.recurrence_rule and start != instance.start:
        validated_data['recurrence_rule'] = shift_recurrence_rule_for_user(
            instance.recurrence_rule, instance.start, start, user)
        if 'exception_dates' not in validated_data:
            validated_data['exception_dates'] = datetimeutils.shift_exception_dates(
                instance.exception_dates, instance.start, start, ZoneInfo(user.settings.time_zone))

    if instance is not None and instance.recurrence_rule and 'recurrence_rule' in validated_data \
            and not validated_data['recurrence_rule']:
        reminderservice.collapse_reminder_series(instance)


def bound_to_course(rule, start, end, all_day, course):
    """
    Return a repeating Homework's ``rule`` ending by its class's last day: a rule without ``COUNT`` or ``UNTIL`` is
    given an ``UNTIL`` at the end of ``course.end_date``.

    :raises ValidationError: if the rule then has no occurrences, or more than ``MAX_HOMEWORK_OCCURRENCES``
    """
    tz = ZoneInfo(course.get_user().settings.time_zone)
    prefix, parts = parse_recurrence_rule(rule)
    if 'COUNT' not in parts and 'UNTIL' not in parts:
        parts['UNTIL'] = datetimeutils.end_of_day_until(course.end_date, tz)
        rule = join_recurrence_rule(prefix, parts)

    count = sum(1 for _ in itertools.islice(datetimeutils.expand_recurrence(rule, start, end, tz, all_day=all_day),
                                            MAX_HOMEWORK_OCCURRENCES + 1))
    if count == 0:
        raise ValidationError({'recurrence_rule': "It has no dates by the class's last day."})
    if count > MAX_HOMEWORK_OCCURRENCES:
        raise ValidationError({'recurrence_rule': f'It repeats more than {MAX_HOMEWORK_OCCURRENCES} times.'})
    return rule


def find_occurrence(source, occurrence_start):
    """
    Return the ``(start, end)`` of the occurrence of ``source`` beginning at ``occurrence_start``. An item that
    doesn't repeat has only itself as an occurrence.

    :raises ValidationError: if ``occurrence_start`` is not an occurrence of ``source``, or was already excluded
    """
    if not source.recurrence_rule:
        if occurrence_start != source.start:
            raise ValidationError({'occurrence_start': f'Not an occurrence of this {_noun(source)}.'})
        return source.start, source.end

    first = next(source.occurrences(not_before=occurrence_start), None)
    if first is None or first[0] != occurrence_start:
        raise ValidationError({'occurrence_start': f'Not an occurrence of this {_noun(source)}.'})

    return first


def series_bounds_for_occurrence_move(source, occurrence_start, new_start, new_end):
    """
    Return the ``(start, end)`` that moves the whole series of ``source`` the way its occurrence at
    ``occurrence_start`` moved to ``new_start``..``new_end``.

    :raises ValidationError: if ``occurrence_start`` is not an occurrence of the series
    """
    find_occurrence(source, occurrence_start)
    tz = ZoneInfo(source.get_user().settings.time_zone)
    return datetimeutils.shifted_series_bounds(source.start, occurrence_start, new_start, new_end, tz,
                                               all_day=source.all_day)


def detach_occurrence(source, occurrence_start):
    """
    Make one occurrence of a repeating Event or Homework its own item, with the series' content and reminders, and
    leave it out of the series. The series keeps its note and attachments, unless that was its last remaining
    occurrence: they then move to the new item and the series is deleted.

    :return: The new item.
    :raises ValidationError: if ``source`` does not repeat, or ``occurrence_start`` is not one of its occurrences
    """
    if not source.recurrence_rule:
        raise ValidationError(f"This {_noun(source)} doesn't repeat.")

    start, end = find_occurrence(source, occurrence_start)
    values = {field: getattr(source, field) for field in _OCCURRENCE_FIELDS[type(source)]}
    if isinstance(source, Homework):
        values.update(current_grade=enums.UNGRADED, completed=False)

    with transaction.atomic():
        detached = type(source).objects.create(start=start, end=end, **values)
        if isinstance(source, Homework):
            detached.resources.set(source.resources.all())
        reminderservice.clone_reminders(source, detached)

        _exclude(source, occurrence_start)

        if next(source.occurrences(), None) is None:
            is_homework = isinstance(source, Homework)
            for note in source.notes_set.all():
                linked = note.homework if is_homework else note.events
                linked.add(detached)
                linked.remove(source)
            source.attachments.update(**{'homework' if is_homework else 'event': detached})
            source.delete()

    logger.info(f"{type(source).__name__} {source.pk} occurrence {occurrence_start.isoformat()} detached to "
                f"{detached.pk} for user {source.get_user().pk}")

    return detached


def exclude_occurrence(source, occurrence_start):
    """
    Delete one occurrence of a repeating Event or Homework. Deleting its last remaining occurrence deletes the series.

    :return: The series, or None when it was deleted.
    :raises ValidationError: if ``source`` does not repeat, or ``occurrence_start`` is not one of its occurrences
    """
    if not source.recurrence_rule:
        raise ValidationError(f"This {_noun(source)} doesn't repeat.")

    find_occurrence(source, occurrence_start)

    with transaction.atomic():
        _exclude(source, occurrence_start)
        if next(source.occurrences(), None) is None:
            source.delete()
            return None

    return source


def _noun(item):
    return item._meta.verbose_name.lower()


def _exclude(source, occurrence_start):
    source.exception_dates = [*(source.exception_dates or []), datetimeutils.as_utc_iso(occurrence_start)]
    source.save(update_fields=['exception_dates', 'updated_at'])
