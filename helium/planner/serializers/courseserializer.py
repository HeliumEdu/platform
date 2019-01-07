import logging

from rest_framework import serializers

from helium.planner.models import Course, CourseGroup
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)


class CourseSerializer(serializers.ModelSerializer):
    schedules = CourseScheduleSerializer(many=True, required=False, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course_group'].queryset = CourseGroup.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'room', 'credits', 'color', 'website', 'is_online', 'current_grade', 'trend', 'teacher_name',
            'teacher_email', 'start_date', 'end_date', 'schedules', 'course_group',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'has_weighted_grading', 'num_homework', 'num_homework_completed',
            'num_homework_graded',)
        read_only_fields = (
            'current_grade', 'trend', 'num_days', 'num_days_completed', 'has_weighted_grading',
            'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def validate(self, attrs):
        start_date = attrs.get('start_date', None)
        if not start_date and self.instance:
            start_date = self.instance.start_date
        end_date = attrs.get('end_date', None)
        if not end_date and self.instance:
            end_date = self.instance.end_date

        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("The 'start_date' must be before the 'end_date'")

        return attrs
