__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import logging

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.common.serializers.fields import ExceptionDatesField, TzAwareDateTimeField
from helium.common.utils.versionutils import client_version_gte
from helium.planner.models import CourseSchedule
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)

_DAYS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
_MIDNIGHT = datetime.time(0, 0, 0)

MULTIPLE_SCHEDULES_MIN_VERSION = '3.8.0'


def get_gated_schedules(schedules, request):
    """
    Below `MULTIPLE_SCHEDULES_MIN_VERSION`, truncate `schedules` to at most
    one entry per course (the earliest-created), preserving the single-
    schedule-per-course contract those clients' UI assumes — `schedules` may
    span more than one course (e.g. the user-wide list endpoint), so this
    can't be a flat `[:1]`. `schedules` must already be ordered by `id` by
    the caller. At or above the gate, `schedules` is returned unmodified.

    `request` is None for non-HTTP serialization (e.g. data export) — there's
    no client version to gate against there, so nothing is truncated.
    """
    if request is None or client_version_gte(request, MULTIPLE_SCHEDULES_MIN_VERSION):
        return schedules

    seen_course_ids = set()
    gated_schedules = []
    for schedule in schedules:
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
    A class's recurring weekly schedule, defined by `days_of_week` and the
    per-day `*_start_time` / `*_end_time` fields — the writable, canonical
    representation. `recurrence_groups` is the derived, read-only rendering of
    that same data: exceptions from `Course.exceptions` / `CourseGroup.exceptions`
    already merged in, ready to hand to a recurrence-aware calendar widget
    without recomputing anything client-side.

    Clients that send an `X-Client-Version` header of `3.8.0` or higher
    receive every schedule for the course and may create more than one;
    clients below that version (or that omit the header) only ever see and
    may only ever create a single schedule per course, matching the
    single-schedule contract those clients' UI was built against.
    """

    recurrence_groups = serializers.SerializerMethodField()

    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'days_of_week', 'sun_start_time', 'sun_end_time', 'mon_start_time', 'mon_end_time', 'tue_start_time',
            'tue_end_time', 'wed_start_time', 'wed_end_time', 'thu_start_time', 'thu_end_time', 'fri_start_time',
            'fri_end_time', 'sat_start_time', 'sat_end_time', 'course', 'recurrence_groups')
        read_only_fields = ('course',)
        extra_kwargs = {
            'days_of_week': {'required': True},
        }

    @extend_schema_field(CourseScheduleRecurrenceGroupSerializer(many=True))
    def get_recurrence_groups(self, obj):
        groups = coursescheduleservice.course_schedule_to_recurrence_groups(obj.course, obj)

        return CourseScheduleRecurrenceGroupSerializer(groups, many=True).data

    def validate(self, attrs):
        if not self.instance:
            course_id = self.context['view'].kwargs.get('course')
            request = self.context.get('request')

            if request is not None and not client_version_gte(request, MULTIPLE_SCHEDULES_MIN_VERSION) \
                    and CourseSchedule.objects.for_course(course_id).exists():
                raise ValidationError(
                    f'Class {course_id} already has a schedule and there cannot be more than one.')

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

        return attrs
