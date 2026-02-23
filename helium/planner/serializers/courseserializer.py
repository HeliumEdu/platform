__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from rest_framework import serializers

from helium.planner.models import Course, CourseGroup
from helium.planner.serializers.coursescheduleserializer import CourseScheduleSerializer

logger = logging.getLogger(__name__)


class CourseSerializer(serializers.ModelSerializer):
    schedules = CourseScheduleSerializer(many=True, required=False, read_only=True)
    num_homework = serializers.SerializerMethodField()
    num_homework_completed = serializers.SerializerMethodField()
    num_homework_graded = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.context.get('request', None):
            self.fields['course_group'].queryset = CourseGroup.objects.for_user(self.context['request'].user.pk)

    class Meta:
        model = Course
        fields = (
            'id', 'title', 'room', 'credits', 'color', 'website', 'is_online', 'current_grade', 'trend', 'teacher_name',
            'teacher_email', 'start_date', 'end_date', 'exceptions', 'schedules', 'course_group',
            # Property fields (which should also be declared as read-only)
            'num_days', 'num_days_completed', 'has_weighted_grading', 'num_homework', 'num_homework_completed',
            'num_homework_graded',)
        read_only_fields = (
            'course_group', 'current_grade', 'trend', 'num_days', 'num_days_completed', 'has_weighted_grading',
            'num_homework', 'num_homework_completed', 'num_homework_graded',)

    def get_num_homework(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework', 0)

    def get_num_homework_completed(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework_completed', 0)

    def get_num_homework_graded(self, obj) -> int:
        # Use annotated value if available, otherwise default to 0
        # (avoids N+1 queries; newly created courses have no homework anyway)
        return getattr(obj, 'annotated_num_homework_graded', 0)

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
