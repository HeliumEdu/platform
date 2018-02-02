import logging

from rest_framework import serializers

from helium.planner.models import CourseGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseGroup
        fields = (
            'id', 'title', 'start_date', 'end_date', 'shown_on_calendar', 'average_grade', 'trend', 'private_slug',
            'user',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'num_homework', 'num_homework_completed', 'num_homework_graded',)
        read_only_fields = (
            'average_grade', 'trend', 'private_slug', 'user', 'num_days', 'num_days_completed', 'num_homework',
            'num_homework_completed', 'num_homework_graded',)

    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("The 'start_date' must be before the 'end_date'")

        return attrs
