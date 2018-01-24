import logging

from rest_framework import serializers

from helium.planner.models import CourseGroup

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class CourseGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseGroup
        fields = (
            'id', 'title', 'start_date', 'end_date', 'shown_on_calendar', 'average_grade', 'trend', 'private_slug',
            'user',
            # Property fields (which should also be declared as read-only)
            'percent_thru', 'days_remaining', 'num_items', 'num_complete', 'num_incomplete', 'num_graded',)
        read_only_fields = (
            'average_grade', 'trend', 'private_slug', 'user', 'percent_thru', 'days_remaining', 'num_items',
            'num_complete', 'num_incomplete', 'num_graded',)
