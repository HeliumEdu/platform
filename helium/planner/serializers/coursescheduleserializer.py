__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import logging

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from helium.planner.models import CourseSchedule

logger = logging.getLogger(__name__)


class CourseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'days_of_week', 'sun_start_time', 'sun_end_time', 'mon_start_time', 'mon_end_time', 'tue_start_time',
            'tue_end_time', 'wed_start_time', 'wed_end_time', 'thu_start_time', 'thu_end_time', 'fri_start_time',
            'fri_end_time', 'sat_start_time', 'sat_end_time', 'course')
        read_only_fields = ('course',)

    def validate(self, attrs):
        if not self.instance:
            course_id = self.context['view'].kwargs.get('course')

            if CourseSchedule.objects.for_course(course_id).exists():
                raise ValidationError(
                    f'Course {course_id} already has a CourseSchedule and there cannot be more than one.')

        return attrs
