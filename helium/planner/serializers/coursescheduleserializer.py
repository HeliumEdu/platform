import logging

from rest_framework import serializers

from helium.planner.models import CourseSchedule

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


class CourseScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseSchedule
        fields = (
            'id', 'days_of_week', 'sun_start_time', 'sun_end_time', 'mon_start_time', 'mon_end_time', 'tue_start_time',
            'tue_end_time', 'wed_start_time', 'wed_end_time', 'thu_start_time', 'thu_end_time', 'fri_start_time',
            'fri_end_time', 'sat_start_time', 'sat_end_time', 'course')
        read_only_fields = ('course',)
