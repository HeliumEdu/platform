__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import datetime
import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django.conf import settings

from helium.common import enums
from helium.common.serializers.fields import ExceptionDatesField, TzAwareDateTimeField
from helium.common.utils.versionutils import client_version_gte
from helium.planner.models import CourseSchedule
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)

_DAYS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
_MIDNIGHT = datetime.time(0, 0, 0)
_MAX_CYCLE_LENGTH = 20

# Cycle length -> the preset template that represents it, so `template` can be derived
# from a schedule's raw fields (and cleared when they no longer match any preset).
_CYCLE_LENGTH_TO_TEMPLATE = {
    spec['fields']['cycle_length']: template_id
    for template_id, spec in enums.SCHEDULE_TEMPLATES.items()
    if 'cycle_length' in spec['fields']
}



def get_gated_schedules(schedules, request):
    """
    Below `ADVANCED_SCHEDULES_MIN_VERSION`, reduce `schedules` to what a older clients
    understands: at most one **weekly** schedule per course. Rotating rows — day cycles *and*
    week-based ("Week A/B") rotations — are dropped entirely: there's nothing meaningful for such a
    client to render, and it wouldn't understand the rotation config (a week-based row would
    otherwise misrender as an every-week schedule). Dropping rotating rows first also means the
    single-schedule truncation naturally *prefers a weekly row*: a course with a weekly + a rotating
    schedule hands the client its weekly one, never a rotating row.

    `schedules` may span more than one course (e.g. the user-wide list endpoint), so this can't be
    a flat `[:1]`, and must already be ordered by `id` by the caller so the retained weekly row is
    the earliest-created. At or above the gate, `schedules` is returned unmodified.

    `request` is None for non-HTTP serialization (e.g. data export) — there's no client version to
    gate against there, so nothing is dropped.
    """
    if request is None or client_version_gte(request, settings.ADVANCED_SCHEDULES_MIN_VERSION):
        return schedules

    seen_course_ids = set()
    gated_schedules = []
    for schedule in schedules:
        if schedule.is_rotating:
            continue
        if schedule.course_id not in seen_course_ids:
            seen_course_ids.add(schedule.course_id)
            gated_schedules.append(schedule)

    return gated_schedules


class CourseScheduleRecurrenceGroupSerializer(serializers.Serializer):
    """
    One recurring occurrence definition derived from a `CourseSchedule` — a
    unique (days, start_time, end_time) combination among its active days,
    already resolved into an iCal `recurrence_rule` and `exception_dates`. A
    schedule with Mon/Wed/Fri at 9am and Thu at 2pm produces two of these.
    """
    start = TzAwareDateTimeField()
    end = TzAwareDateTimeField()
    recurrence_rule = serializers.CharField()
    exception_dates = ExceptionDatesField()


class CourseScheduleSerializer(serializers.ModelSerializer):
    """
    A class's schedule. Three shapes:

    - **Weekly** (`cycle_length` null and `is_week_based` false): defined by `days_of_week`
      and the per-day `*_start_time` / `*_end_time` fields — the writable, canonical form.
    - **Day cycle** (`cycle_length` set): a day-based rotation defined by `cycle_length` +
      `anchor_date` + `cycle_slots`; the weekly fields are ignored.
    - **Week-based** (`is_week_based` true): a calendar-week rotation that reuses the weekly
      fields but only meets every other week, on the week matching `week_offset`.

    `recurrence_groups` is the derived, read-only rendering of whichever shape
    applies: exceptions from `Course.exceptions` / `CourseGroup.exceptions` already
    merged in, ready to hand to a recurrence-aware calendar widget without
    recomputing anything client-side — so the client renders weekly and cycle
    schedules identically.
    """

    recurrence_groups = serializers.SerializerMethodField()

    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'days_of_week', 'sun_start_time', 'sun_end_time', 'mon_start_time', 'mon_end_time', 'tue_start_time',
            'tue_end_time', 'wed_start_time', 'wed_end_time', 'thu_start_time', 'thu_end_time', 'fri_start_time',
            'fri_end_time', 'sat_start_time', 'sat_end_time', 'course', 'cycle_length', 'anchor_date', 'cycle_slots',
            'is_week_based', 'week_offset', 'start_date', 'end_date', 'template', 'recurrence_groups')
        read_only_fields = ('course',)
        extra_kwargs = {
            'days_of_week': {'required': True},
        }

    @extend_schema_field(CourseScheduleRecurrenceGroupSerializer(many=True))
    def get_recurrence_groups(self, obj):
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(obj.course, obj)

        return CourseScheduleRecurrenceGroupSerializer(groups, many=True).data

    def _resolve(self, attrs, key):
        """Effective value of ``key`` for validation: the submitted value if present
        (including an explicit null), else the instance's current value on update."""
        if key in attrs:
            return attrs[key]
        return getattr(self.instance, key) if self.instance else None

    def validate(self, attrs):
        # A `template` sent in this request fills the rotation fields it implies, but
        # only as defaults — the client's own fields win (see `_apply_template_defaults`).
        if attrs.get('template') is not None:
            self._apply_template_defaults(attrs, attrs['template'])

        cycle_length = self._resolve(attrs, 'cycle_length')
        is_week_based = self._resolve(attrs, 'is_week_based')

        if cycle_length is not None and is_week_based:
            raise ValidationError("A schedule cannot be both a day cycle ('cycle_length') and a week-based "
                                  "rotation ('is_week_based').")

        if cycle_length is not None:
            self._validate_cycle(cycle_length, self._resolve(attrs, 'anchor_date'),
                                 self._resolve(attrs, 'cycle_slots'))
        elif is_week_based:
            self._validate_week_based(self._resolve(attrs, 'week_offset'),
                                      self._resolve(attrs, 'anchor_date'), attrs)
            self._require_meeting_day(attrs)
        else:
            if attrs.get('anchor_date') is not None or attrs.get('cycle_slots') is not None \
                    or attrs.get('week_offset') is not None:
                raise ValidationError("'anchor_date', 'cycle_slots', and 'week_offset' are only valid on a "
                                      "rotating schedule.")
            self._validate_weekly(attrs)
            request = self.context.get('request')
            if request is not None and client_version_gte(request, settings.ADVANCED_SCHEDULES_MIN_VERSION):
                self._require_meeting_day(attrs)

        # `template` is canonical: derived from the resulting rotation shape, so raw fields
        # matching a preset get it filled in and edits that no longer match clear it — the
        # API self-heals rather than letting `template` drift out of sync with the fields.
        attrs['template'] = self._canonical_template(cycle_length, is_week_based)

        start_date = self._resolve(attrs, 'start_date')
        end_date = self._resolve(attrs, 'end_date')
        if start_date and end_date and start_date > end_date:
            raise ValidationError("The 'start_date' must be before the 'end_date'")

        return attrs

    def _apply_template_defaults(self, attrs, template):
        # Fill the fields a template implies, but only where the client didn't set them
        # (client fields win, and `template` is re-derived from the result). Stale state the
        # template doesn't own — e.g. the other rotation type when switching — is cleared.
        fields = enums.SCHEDULE_TEMPLATES[template]['fields']
        is_cycle = 'cycle_length' in fields
        is_week = 'is_week_based' in fields
        for key, value in fields.items():
            attrs.setdefault(key, value)
        if not is_cycle:
            attrs.setdefault('cycle_length', None)
            attrs.setdefault('cycle_slots', None)
        if not is_week:
            attrs.setdefault('is_week_based', False)
            attrs.setdefault('week_offset', None)
        if not (is_cycle or is_week):
            attrs.setdefault('anchor_date', None)

    def _canonical_template(self, cycle_length, is_week_based):
        # The preset a shape maps to, or None for a custom cycle length or a plain weekly
        # schedule. Keeps `template` a pure function of the rotation fields.
        if is_week_based:
            return enums.WEEK_AB
        if cycle_length is not None:
            return _CYCLE_LENGTH_TO_TEMPLATE.get(cycle_length)
        return None

    def _validate_week_based(self, week_offset, anchor_date, attrs):
        if anchor_date is None:
            raise ValidationError("'anchor_date' is required for a week-based rotation.")
        if week_offset not in (0, 1):
            raise ValidationError("'week_offset' must be 0 (Week A) or 1 (Week B).")

        self._validate_weekly(attrs)

    def _validate_cycle(self, cycle_length, anchor_date, cycle_slots):
        if not 2 <= cycle_length <= _MAX_CYCLE_LENGTH:
            raise ValidationError(f"'cycle_length' must be between 2 and {_MAX_CYCLE_LENGTH}.")
        if anchor_date is None:
            raise ValidationError("'anchor_date' is required for a cycle schedule.")
        if not cycle_slots:
            raise ValidationError("'cycle_slots' must be a non-empty list for a cycle schedule.")

        seen_indices = set()
        for slot in cycle_slots:
            indices = slot.get('indices') if isinstance(slot, dict) else None
            if not indices or not all(isinstance(i, int) and 1 <= i <= cycle_length for i in indices):
                raise ValidationError(
                    f"Each cycle slot's 'indices' must be a non-empty list of integers in [1, {cycle_length}].")
            if seen_indices.intersection(indices):
                raise ValidationError("A cycle-day index cannot appear in more than one slot.")
            seen_indices.update(indices)

            try:
                start_time = datetime.time.fromisoformat(slot['start_time'])
                end_time = datetime.time.fromisoformat(slot['end_time'])
            except (KeyError, TypeError, ValueError):
                raise ValidationError("Each cycle slot needs 'start_time' and 'end_time' as 'HH:MM:SS'.")
            if start_time > end_time:
                raise ValidationError("A cycle slot's 'start_time' must be before its 'end_time'.")

    def _validate_weekly(self, attrs):
        days_of_week = attrs.get('days_of_week')
        if days_of_week is None and self.instance:
            days_of_week = self.instance.days_of_week

        for i, day in enumerate(_DAYS):
            start_key = f'{day}_start_time'
            end_key = f'{day}_end_time'

            start_time = attrs.get(start_key)
            if start_time is None and self.instance:
                start_time = getattr(self.instance, start_key)

            end_time = attrs.get(end_key)
            if end_time is None and self.instance:
                end_time = getattr(self.instance, end_key)

            if start_time and end_time and start_time > end_time:
                raise ValidationError(f"The 'start_time' of '{day}' must be before 'end_time'")

            if days_of_week and days_of_week[i] == '1' and (start_time == _MIDNIGHT or end_time == _MIDNIGHT):
                raise ValidationError(
                    f"'{day}' is marked active in 'days_of_week' but '{day}_start_time' / '{day}_end_time' "
                    f"are `00:00:00`. Set non-zero meeting times for active days, or mark the day inactive "
                    f"in 'days_of_week'."
                )

    def _require_meeting_day(self, attrs):
        days_of_week = attrs.get('days_of_week')
        if days_of_week is None and self.instance:
            days_of_week = self.instance.days_of_week
        if not days_of_week or '1' not in days_of_week:
            raise ValidationError("A schedule must meet on at least one day.")
