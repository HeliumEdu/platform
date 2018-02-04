import logging

from rest_framework import serializers

from helium.planner.models import Course

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.1'

logger = logging.getLogger(__name__)


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = (
            'id', 'title', 'room', 'credits', 'color', 'website', 'is_online', 'current_grade', 'trend', 'private_slug',
            'teacher_name', 'teacher_email', 'start_date', 'end_date', 'days_of_week', 'sun_start_time', 'sun_end_time',
            'mon_start_time', 'mon_end_time', 'tue_start_time', 'tue_end_time', 'wed_start_time', 'wed_end_time',
            'thu_start_time', 'thu_end_time', 'fri_start_time', 'fri_end_time', 'sat_start_time', 'sat_end_time',
            'days_of_week_alt', 'sun_start_time_alt', 'sun_end_time_alt', 'mon_start_time_alt', 'mon_end_time_alt',
            'tue_start_time_alt', 'tue_end_time_alt', 'wed_start_time_alt', 'wed_end_time_alt', 'thu_start_time_alt',
            'thu_end_time_alt', 'fri_start_time_alt', 'fri_end_time_alt', 'sat_start_time_alt', 'sat_end_time_alt',
            'course_group',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'has_weighted_grading', 'num_homework', 'num_homework_completed',
            'num_homework_graded',)
        read_only_fields = (
            'current_grade', 'trend', 'private_slug', 'num_days', 'num_days_completed', 'has_weighted_grading',
            'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def validate(self, attrs):
        start_date = self.instance.start_date if self.instance else attrs.get('start_date', None)
        end_date = self.instance.end_date if self.instance else attrs.get('end_date', None)

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("The 'start_date' must be before the 'end_date'")

        return attrs
