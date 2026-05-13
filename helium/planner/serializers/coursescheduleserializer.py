__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models import CourseSchedule

logger = logging.getLogger(__name__)

_DAYS = ('sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat')
_MIDNIGHT = datetime.time(0, 0, 0)


class CourseScheduleSerializer(serializers.ModelSerializer):
    """
    A class's recurring weekly schedule. Meeting occurrences are computed
    client-side — walk dates between `Course.start_date` and
    `Course.end_date`, keep ones where `days_of_week` is `1` for that
    weekday, drop ones listed in `Course.exceptions` /
    `CourseGroup.exceptions`. Day-of-week times are interpreted in
    `settings.time_zone` (see `/auth/user/`).
    """

    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'days_of_week', 'sun_start_time', 'sun_end_time', 'mon_start_time', 'mon_end_time', 'tue_start_time',
            'tue_end_time', 'wed_start_time', 'wed_end_time', 'thu_start_time', 'thu_end_time', 'fri_start_time',
            'fri_end_time', 'sat_start_time', 'sat_end_time', 'course')
        read_only_fields = ('course',)
        extra_kwargs = {
            'days_of_week': {'required': True},
        }

    def validate(self, attrs):
        if not self.instance:
            course_id = self.context['view'].kwargs.get('course')

            if CourseSchedule.objects.for_course(course_id).exists():
                raise ValidationError(
                    f'Course {course_id} already has a CourseSchedule and there cannot be more than one.')

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
